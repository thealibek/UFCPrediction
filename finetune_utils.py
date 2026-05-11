"""Fine-Tuning utilities для UFC Predictor.

Что делает модуль:
1. Строит обучающий датасет (JSONL) из локальной базы бойцов + исторических боёв
   из rag_seed + резолвнутых прогнозов из history.json.
2. Запускает OpenAI fine-tuning через их API (загрузка файла + создание job + polling).
3. Генерирует готовый `train_lora.py` скрипт для запуска LoRA/QLoRA на Colab/локально
   через Hugging Face transformers + PEFT.
4. Хранит реестр кастомных моделей в `./custom_models.json` — чтобы пользователь мог
   выбрать ft-модель в сайдбаре приложения.

Дизайн: тяжёлое обучение (LoRA, GPU) НЕ запускается внутри Streamlit — мы генерируем
скрипт и инструкции. OpenAI FT можно триггерить из UI, потому что вычисления у них.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CUSTOM_MODELS_FILE = "./custom_models.json"
TRAINING_DATA_DIR = "./training_data"
Path(TRAINING_DATA_DIR).mkdir(exist_ok=True)


SYSTEM_PROMPT_FT = (
    "You are an elite UFC fight analyst trained on real fight outcomes, fighter profiles, "
    "and historical stylistic matchups. For every prediction request, output STRICTLY in "
    "this markdown structure:\n\n"
    "### 🎯 ПРОГНОЗ\n"
    "Победитель: **[Name]** — XX% уверенности.\n"
    "Метод: KO/TKO XX% · Submission XX% · Decision XX%.\n"
    "Раунд (если финиш): R[1-5].\n\n"
    "### 📊 АНАЛИТИКА\n"
    "[2-3 коротких абзаца. Стилевой матч-ап с цифрами и MMA-сленгом.]\n\n"
    "### 💰 ЛУЧШАЯ СТАВКА\n"
    "[Конкретно: ML / Method / Round / Total + где value.]\n\n"
    "### ⚠️ РИСКИ\n"
    "[2-4 жёстких сценария почему ставка может не зайти.]\n\n"
    "Be confident, sharp, calibrated. Use real fighter data when provided."
)


# ---------------------------------------------------------------------------
# Dataset building
# ---------------------------------------------------------------------------

def _fighter_brief(f: dict) -> str:
    """Компактное представление бойца для prompt."""
    return (
        f"{f.get('name','?')} ({f.get('country','')}, {f.get('age','?')} лет, "
        f"{f.get('record','?')}, stance: {f.get('stance','?')}). "
        f"Style: {f.get('style','?')}. "
        f"SLpM {f.get('SLpM','?')}, StrAcc {f.get('StrAcc','?')}%, "
        f"StrDef {f.get('StrDef','?')}%, TDAvg {f.get('TDAvg','?')}, "
        f"TDDef {f.get('TDDef','?')}%, SubAvg {f.get('SubAvg','?')}. "
        f"Strengths: {', '.join(f.get('strengths',[]) or [])}. "
        f"Weaknesses: {', '.join(f.get('weaknesses',[]) or [])}."
    )


def _format_assistant_response(
    winner: str, method: str, round_n: int,
    notes: str = "", lessons: str = "",
    win_pct: int = 65,
) -> str:
    """Фабрика ground-truth ответа в нужном формате."""
    method_lower = (method or "").lower()
    if "ko" in method_lower or "tko" in method_lower:
        ko, sub, dec = 65, 10, 25
    elif "sub" in method_lower:
        ko, sub, dec = 15, 60, 25
    else:
        ko, sub, dec = 20, 10, 70

    risks_default = (
        "- Counter-strike с дистанции при ошибке pressure.\n"
        "- Затяжка боя в late rounds снижает edge фаворита.\n"
        "- Cardio просадка при тяжёлой весогонке."
    )

    return (
        f"### 🎯 ПРОГНОЗ\n"
        f"Победитель: **{winner}** — {win_pct}% уверенности.\n"
        f"Метод: KO/TKO {ko}% · Submission {sub}% · Decision {dec}%.\n"
        f"Раунд (если финиш): R{round_n}.\n\n"
        f"### 📊 АНАЛИТИКА\n"
        f"{notes or 'Стилистический матч-ап решает: технический + физический edge на стороне победителя.'}\n\n"
        f"### 💰 ЛУЧШАЯ СТАВКА\n"
        f"{winner} ML или {winner} by {method or 'Decision'}.\n\n"
        f"### ⚠️ РИСКИ\n"
        f"{lessons or risks_default}"
    )


def build_dataset_from_historical(historical_fights: list[dict]) -> list[dict]:
    """Из rag_seed.HISTORICAL_FIGHTS делаем supervised examples."""
    examples = []
    for fight in historical_fights:
        a = fight.get("fighter_a")
        b = fight.get("fighter_b")
        if not a or not b:
            continue
        winner = fight.get("winner", a)
        method = fight.get("method", "Decision")
        rnd = int(fight.get("round", 3) or 3)

        user_msg = (
            f"Дай прогноз на бой UFC.\n\n"
            f"ИВЕНТ: {fight.get('event','UFC')}\n"
            f"ВЕСОВАЯ: {fight.get('weight_class','?')}\n"
            f"БОЙ: {a} vs {b}\n"
        )
        assistant_msg = _format_assistant_response(
            winner=winner, method=method, round_n=rnd,
            notes=fight.get("notes", ""),
            lessons=fight.get("stylistic_lessons", ""),
            win_pct=72,
        )
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_FT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            "_meta": {"source": "historical_fight", "id": fight.get("id", "")},
        })
    return examples


def build_dataset_from_history(history: list[dict], fighters: list[dict]) -> list[dict]:
    """Из резолвнутых (won/lost) прогнозов делаем examples с реальным исходом."""
    examples = []
    fmap = {f.get("name", "").lower(): f for f in (fighters or [])}

    for h in history:
        if h.get("status") not in ("won", "lost"):
            continue
        if not h.get("actual_winner"):
            continue
        a = h.get("fa") or h.get("fighter_a")
        b = h.get("fb") or h.get("fighter_b")
        if not a or not b:
            continue
        fa = fmap.get(a.lower(), {})
        fb = fmap.get(b.lower(), {})

        user_msg = (
            f"Дай прогноз на бой UFC.\n\n"
            f"ИВЕНТ: {h.get('event','UFC')}\n"
            f"ВЕСОВАЯ: {h.get('weight_class','?')}\n"
            f"БОЙ: {a} vs {b}\n"
        )
        if fa:
            user_msg += f"\nДАННЫЕ A: {_fighter_brief(fa)}\n"
        if fb:
            user_msg += f"ДАННЫЕ B: {_fighter_brief(fb)}\n"

        method = h.get("actual_method", "Decision") or "Decision"
        # Win % из реального outcome — даём 70-80 как разумный прогноз для трейн
        assistant_msg = _format_assistant_response(
            winner=h["actual_winner"],
            method=method,
            round_n=3,
            notes=f"Реальный исход подтвердил стилистический edge {h['actual_winner']}.",
            lessons="",
            win_pct=70,
        )
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_FT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            "_meta": {"source": "resolved_prediction", "id": h.get("id", "")},
        })
    return examples


def build_full_dataset(
    fighters: list[dict],
    history: list[dict],
) -> dict:
    """Главная сборка датасета. Возвращает {'examples': [...], 'stats': {...}}"""
    try:
        from rag_seed import HISTORICAL_FIGHTS
    except ImportError:
        HISTORICAL_FIGHTS = []

    ex_hist = build_dataset_from_historical(HISTORICAL_FIGHTS)
    ex_resolved = build_dataset_from_history(history, fighters)

    examples = ex_hist + ex_resolved

    return {
        "examples": examples,
        "stats": {
            "total": len(examples),
            "from_historical": len(ex_hist),
            "from_resolved_predictions": len(ex_resolved),
        },
    }


def to_jsonl(examples: list[dict], strip_meta: bool = True) -> str:
    """Сериализуем examples в JSONL (одна запись на строку, без _meta)."""
    lines = []
    for e in examples:
        rec = {"messages": e["messages"]}
        if not strip_meta and "_meta" in e:
            rec["_meta"] = e["_meta"]
        lines.append(json.dumps(rec, ensure_ascii=False))
    return "\n".join(lines)


def save_jsonl(examples: list[dict], filename: str | None = None) -> str:
    """Сохраняем JSONL на диск, возвращаем путь."""
    if not filename:
        filename = f"ufc_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    path = os.path.join(TRAINING_DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_jsonl(examples))
    return path


def split_train_val(examples: list[dict], val_ratio: float = 0.1) -> tuple[list, list]:
    import random
    rng = random.Random(42)
    items = list(examples)
    rng.shuffle(items)
    n_val = max(1, int(len(items) * val_ratio))
    return items[n_val:], items[:n_val]


# ---------------------------------------------------------------------------
# OpenAI Fine-Tuning API
# ---------------------------------------------------------------------------

def openai_upload_file(api_key: str, jsonl_path: str, base_url: str | None = None) -> str:
    """Загружаем JSONL в OpenAI, возвращаем file_id."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    with open(jsonl_path, "rb") as f:
        result = client.files.create(file=f, purpose="fine-tune")
    return result.id


def openai_create_finetune(
    api_key: str,
    training_file_id: str,
    base_model: str = "gpt-4o-mini-2024-07-18",
    suffix: str = "ufc-v1",
    n_epochs: int = 3,
    base_url: str | None = None,
) -> dict:
    """Создаём fine-tuning job. Возвращает dict job-а."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    job = client.fine_tuning.jobs.create(
        training_file=training_file_id,
        model=base_model,
        suffix=suffix,
        hyperparameters={"n_epochs": n_epochs},
    )
    return job.model_dump() if hasattr(job, "model_dump") else dict(job)


def openai_get_finetune_status(api_key: str, job_id: str, base_url: str | None = None) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    job = client.fine_tuning.jobs.retrieve(job_id)
    return job.model_dump() if hasattr(job, "model_dump") else dict(job)


# ---------------------------------------------------------------------------
# LoRA training script generator (HuggingFace + PEFT)
# ---------------------------------------------------------------------------

def generate_lora_script(
    base_model: str = "meta-llama/Llama-3.2-3B-Instruct",
    train_file: str = "./training_data/ufc_train.jsonl",
    val_file: str | None = None,
    output_dir: str = "./ufc-lora-out",
    use_qlora: bool = True,
    epochs: int = 3,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    batch_size: int = 4,
    grad_accum: int = 4,
    max_seq_length: int = 2048,
) -> str:
    """Генерируем готовый train_lora.py для запуска на Colab T4 / локально."""

    quant_block = ""
    model_load_kwargs = "torch_dtype=torch.bfloat16"
    if use_qlora:
        quant_block = """
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
"""
        model_load_kwargs = "quantization_config=bnb_config, torch_dtype=torch.bfloat16"

    val_path_line = f'"{val_file}"' if val_file else "None"

    script = f'''"""
UFC Predictor — LoRA{"/QLoRA" if use_qlora else ""} fine-tuning script.
Сгенерировано Streamlit-приложением.

Запуск (Colab T4 / RunPod / локальный GPU):
    pip install -U transformers peft bitsandbytes accelerate datasets trl
    python train_lora.py

После окончания: адаптер будет в `{output_dir}/`.
Используй его в приложении: укажи путь как кастомную модель или загрузи на HuggingFace.
"""
import json
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# ============== CONFIG ==============
BASE_MODEL = "{base_model}"
TRAIN_FILE = "{train_file}"
VAL_FILE = {val_path_line}
OUTPUT_DIR = "{output_dir}"
EPOCHS = {epochs}
LR = {learning_rate}
BATCH_SIZE = {batch_size}
GRAD_ACCUM = {grad_accum}
MAX_SEQ_LENGTH = {max_seq_length}
LORA_R = {lora_r}
LORA_ALPHA = {lora_alpha}
{quant_block}

# ============== TOKENIZER ==============
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# ============== MODEL ==============
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    {model_load_kwargs},
    device_map="auto",
    trust_remote_code=True,
)
{"model = prepare_model_for_kbit_training(model)" if use_qlora else ""}

# ============== LORA ==============
lora_config = LoraConfig(
    r=LORA_R, lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ============== DATA ==============
def format_chat(example):
    return {{"text": tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )}}

ds_train = load_dataset("json", data_files=TRAIN_FILE, split="train").map(format_chat)
ds_val = None
if VAL_FILE:
    ds_val = load_dataset("json", data_files=VAL_FILE, split="train").map(format_chat)

# ============== TRAINING ==============
args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LR,
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    eval_strategy="epoch" if ds_val else "no",
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=args,
    train_dataset=ds_train,
    eval_dataset=ds_val,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    packing=False,
)

trainer.train()
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"\\n✅ Готово. Адаптер сохранён в: {{OUTPUT_DIR}}")
print("Можно загрузить на HF Hub или указать локальный путь в приложении.")
'''
    return script


# ---------------------------------------------------------------------------
# Custom models registry
# ---------------------------------------------------------------------------

def list_custom_models() -> list[dict]:
    """Список зарегистрированных кастомных моделей."""
    if not os.path.exists(CUSTOM_MODELS_FILE):
        return []
    try:
        with open(CUSTOM_MODELS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def register_custom_model(record: dict):
    """Добавляем модель в реестр.
    record = {'name','provider','model_id','base_model','created_at','notes'}
    """
    models = list_custom_models()
    # Дедуп по model_id
    models = [m for m in models if m.get("model_id") != record.get("model_id")]
    models.insert(0, record)
    with open(CUSTOM_MODELS_FILE, "w") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)


def remove_custom_model(model_id: str):
    models = [m for m in list_custom_models() if m.get("model_id") != model_id]
    with open(CUSTOM_MODELS_FILE, "w") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)
