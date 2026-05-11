"""Fine-Tuning UI страница — управление обучением кастомной UFC-модели."""
from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from finetune_utils import (
    SYSTEM_PROMPT_FT,
    build_full_dataset,
    generate_lora_script,
    list_custom_models,
    openai_create_finetune,
    openai_get_finetune_status,
    openai_upload_file,
    register_custom_model,
    remove_custom_model,
    save_jsonl,
    split_train_val,
    to_jsonl,
)


def render_finetune_page():
    st.markdown("## 🎓 Model Training / Fine-Tuning")
    st.caption(
        "Дообучаем модель на твоих данных: исторические бои + резолвнутые прогнозы → "
        "кастомная UFC-модель с лучшей калибровкой."
    )

    fighters = st.session_state.get("fighters", [])
    history = st.session_state.get("history", [])

    tab_data, tab_train, tab_jobs, tab_models, tab_help = st.tabs([
        "📊 Dataset",
        "⚙️ Train",
        "🚀 Jobs",
        "🎯 Custom Models",
        "❓ Help",
    ])

    # =====================================================================
    # TAB: DATASET
    # =====================================================================
    with tab_data:
        st.markdown("### 📊 Сборка обучающего датасета")
        st.caption(
            "Источники: исторические бои (rag_seed) + резолвнутые прогнозы из History."
        )

        if st.button("🔄 Пересобрать датасет", use_container_width=True):
            st.session_state.ft_dataset = build_full_dataset(fighters, history)
            st.success("Готово.")

        if "ft_dataset" not in st.session_state:
            st.session_state.ft_dataset = build_full_dataset(fighters, history)

        ds = st.session_state.ft_dataset
        stats = ds["stats"]

        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Всего примеров", stats["total"])
        c2.metric("📜 Из истории UFC", stats["from_historical"])
        c3.metric("🎯 Из твоих прогнозов", stats["from_resolved_predictions"])

        if stats["total"] < 10:
            st.warning(
                "⚠️ Менее 10 примеров — fine-tuning будет неэффективен. "
                "Пометь больше прогнозов как won/lost в History или добавь "
                "исторические бои в Knowledge Base."
            )

        st.markdown("---")
        st.markdown("#### 👁️ Превью первых 3 примеров")
        for i, ex in enumerate(ds["examples"][:3]):
            with st.expander(f"Example #{i+1} · source: `{ex['_meta']['source']}`"):
                st.markdown("**System:**")
                st.code(ex["messages"][0]["content"][:500] + "...", language=None)
                st.markdown("**User:**")
                st.code(ex["messages"][1]["content"], language=None)
                st.markdown("**Assistant (target):**")
                st.code(ex["messages"][2]["content"], language="markdown")

        st.markdown("---")
        st.markdown("#### 📥 Экспорт")

        ec1, ec2, ec3 = st.columns(3)
        val_ratio = ec1.slider("Validation split", 0.0, 0.3, 0.1, 0.05)
        do_split = ec2.checkbox("Разделить train/val", value=True)

        jsonl_str = to_jsonl(ds["examples"])
        ec3.download_button(
            "⬇️ Полный JSONL",
            data=jsonl_str.encode("utf-8"),
            file_name=f"ufc_train_full_{datetime.now().strftime('%Y%m%d')}.jsonl",
            mime="application/jsonl",
            use_container_width=True,
        )

        if do_split and val_ratio > 0:
            train_ex, val_ex = split_train_val(ds["examples"], val_ratio)
            sc1, sc2 = st.columns(2)
            sc1.download_button(
                f"⬇️ Train ({len(train_ex)})",
                data=to_jsonl(train_ex).encode("utf-8"),
                file_name="ufc_train.jsonl",
                mime="application/jsonl", use_container_width=True,
            )
            sc2.download_button(
                f"⬇️ Val ({len(val_ex)})",
                data=to_jsonl(val_ex).encode("utf-8"),
                file_name="ufc_val.jsonl",
                mime="application/jsonl", use_container_width=True,
            )

        if st.button("💾 Сохранить на диск (./training_data/)",
                     use_container_width=True):
            path = save_jsonl(ds["examples"])
            st.success(f"✅ Сохранено: `{path}`")

    # =====================================================================
    # TAB: TRAIN
    # =====================================================================
    with tab_train:
        st.markdown("### ⚙️ Настройка обучения")

        provider = st.radio(
            "Провайдер / метод",
            ["OpenAI Fine-Tuning (cloud)",
             "LoRA / QLoRA (HuggingFace, локально/Colab)",
             "Together.ai / Fireworks (script)"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ============================================================
        # OPENAI
        # ============================================================
        if provider == "OpenAI Fine-Tuning (cloud)":
            st.markdown("#### 🌐 OpenAI Fine-Tuning")
            st.caption(
                "Самый простой вариант: загружаем JSONL → OpenAI обучает у себя → "
                "получаешь model id вида `ft:gpt-4o-mini-...:user:ufc-v1:abc123`."
            )

            base_model = st.selectbox(
                "Базовая модель",
                ["gpt-4o-mini-2024-07-18", "gpt-4.1-mini-2025-04-14",
                 "gpt-4o-2024-08-06", "gpt-3.5-turbo-0125"],
                index=0,
                help="gpt-4o-mini = дёшево + хорошо для большинства случаев.",
            )
            suffix = st.text_input("Suffix модели", value="ufc-v1",
                help="Будет в имени: ft:base:user:[suffix]:hash")
            n_epochs = st.slider("Epochs", 1, 10, 3)

            st.markdown(
                "**Цена ориентир (gpt-4o-mini):** ~$3 за 1M обучающих токенов. "
                "Для 100 примеров ~$0.50–$2."
            )

            api_key_ft = st.session_state.get("api_key_input", "") or st.text_input(
                "OpenAI API Key", type="password",
                help="Берётся из сайдбара если установлен.",
            )

            if st.button("🚀 Запустить OpenAI Fine-Tuning",
                         use_container_width=True, type="primary"):
                if not api_key_ft:
                    st.error("Нужен OpenAI API Key.")
                elif "ft_dataset" not in st.session_state \
                     or st.session_state.ft_dataset["stats"]["total"] < 10:
                    st.error("Сначала собери датасет (вкладка Dataset, ≥10 примеров).")
                else:
                    try:
                        ex = st.session_state.ft_dataset["examples"]
                        with st.spinner("📤 Сохраняю и загружаю датасет..."):
                            path = save_jsonl(ex, "ufc_openai_upload.jsonl")
                            file_id = openai_upload_file(api_key_ft, path)
                        st.info(f"✅ Файл загружен: `{file_id}`")
                        with st.spinner("🚀 Создаю fine-tuning job..."):
                            job = openai_create_finetune(
                                api_key_ft, file_id,
                                base_model=base_model,
                                suffix=suffix,
                                n_epochs=n_epochs,
                            )
                        st.success(f"✅ Job создан: `{job.get('id', '?')}`")
                        st.caption("Иди во вкладку 🚀 Jobs, чтобы трекать прогресс.")
                        # Сохраняем job в session
                        jobs = st.session_state.get("ft_jobs", [])
                        jobs.insert(0, {
                            "id": job.get("id"),
                            "base_model": base_model,
                            "suffix": suffix,
                            "created_at": datetime.now().isoformat(),
                            "status": job.get("status", "queued"),
                        })
                        st.session_state.ft_jobs = jobs
                        st.json(job)
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")

        # ============================================================
        # LORA / QLORA
        # ============================================================
        elif provider == "LoRA / QLoRA (HuggingFace, локально/Colab)":
            st.markdown("#### 🤗 LoRA / QLoRA Training Script")
            st.caption(
                "Генерируем готовый `train_lora.py` — копируешь в Colab "
                "(T4 free) или RunPod, запускаешь, получаешь LoRA-адаптер."
            )

            lc1, lc2 = st.columns(2)
            base_model = lc1.selectbox(
                "Базовая модель",
                [
                    "meta-llama/Llama-3.2-3B-Instruct",
                    "meta-llama/Llama-3.1-8B-Instruct",
                    "Qwen/Qwen2.5-7B-Instruct",
                    "mistralai/Mistral-7B-Instruct-v0.3",
                    "google/gemma-2-9b-it",
                ],
                index=0,
            )
            method = lc2.radio("Метод", ["QLoRA (4bit)", "LoRA (full precision)"],
                              horizontal=True)
            use_qlora = method.startswith("QLoRA")

            pc1, pc2, pc3 = st.columns(3)
            epochs = pc1.number_input("Epochs", 1, 20, 3)
            lr = pc2.number_input("Learning rate", 1e-5, 1e-3, 2e-4,
                                  format="%.6f", step=1e-5)
            lora_r = pc3.number_input("LoRA rank (r)", 4, 128, 16)
            bs = pc1.number_input("Batch size", 1, 32, 4)
            ga = pc2.number_input("Grad accum", 1, 32, 4)
            max_seq = pc3.number_input("Max seq length", 512, 8192, 2048, step=256)
            output_dir = st.text_input("Output dir", "./ufc-lora-out")

            script = generate_lora_script(
                base_model=base_model,
                train_file="./training_data/ufc_train.jsonl",
                val_file="./training_data/ufc_val.jsonl",
                output_dir=output_dir,
                use_qlora=use_qlora,
                epochs=int(epochs),
                learning_rate=float(lr),
                lora_r=int(lora_r),
                batch_size=int(bs),
                grad_accum=int(ga),
                max_seq_length=int(max_seq),
            )

            st.markdown("#### 📜 Сгенерированный скрипт")
            st.code(script, language="python")

            st.download_button(
                "⬇️ Скачать train_lora.py",
                data=script.encode("utf-8"),
                file_name="train_lora.py",
                mime="text/x-python",
                use_container_width=True,
            )

            st.info(
                "**Дальше:**\n"
                "1. Открой Google Colab (T4 GPU бесплатно)\n"
                "2. Загрузи `train_lora.py` + `ufc_train.jsonl` + `ufc_val.jsonl`\n"
                "3. Установи: `!pip install -U transformers peft bitsandbytes accelerate datasets trl`\n"
                "4. Запусти: `!python train_lora.py`\n"
                "5. После ~30 мин получишь LoRA-адаптер в `./ufc-lora-out/`\n"
                "6. Загрузи на HuggingFace Hub или используй локально\n\n"
                "**На RTX 4090 / A100 — берёт минут 5-15 на 100 примеров.**"
            )

        # ============================================================
        # TOGETHER / FIREWORKS
        # ============================================================
        else:
            st.markdown("#### ⚡ Together.ai / Fireworks Fine-Tuning")
            st.caption(
                "Эти платформы дают managed fine-tuning через CLI. Готовим команды."
            )

            platform = st.radio("Платформа", ["Together.ai", "Fireworks AI"],
                                horizontal=True)

            base_model = st.text_input(
                "Base model",
                "meta-llama/Llama-3.1-8B-Instruct" if platform == "Together.ai"
                else "accounts/fireworks/models/llama-v3p1-8b-instruct",
            )
            n_epochs = st.slider("Epochs", 1, 10, 3, key="tf_epochs")
            lr = st.number_input("Learning rate", 1e-6, 1e-3, 1e-5,
                                  format="%.7f", key="tf_lr")

            if platform == "Together.ai":
                cmd = f"""# 1. Установка
pip install --upgrade together

# 2. Логин
export TOGETHER_API_KEY=your_key_here

# 3. Загрузка датасета
together files upload ./training_data/ufc_train.jsonl

# 4. Запуск fine-tuning (вставь file-id из шага 3)
together fine-tuning create \\
    --training-file file-XXXXXXXX \\
    --model {base_model} \\
    --n-epochs {n_epochs} \\
    --learning-rate {lr} \\
    --suffix ufc-v1 \\
    --lora

# 5. Проверка статуса
together fine-tuning list
"""
            else:
                cmd = f"""# 1. Установка
pip install --upgrade firectl

# 2. Логин
firectl signin

# 3. Создаём датасет
firectl create dataset ufc-train \\
    --upload-file ./training_data/ufc_train.jsonl

# 4. Запуск fine-tuning
firectl create fine-tuning-job \\
    --base-model {base_model} \\
    --dataset-id ufc-train \\
    --epochs {n_epochs} \\
    --learning-rate {lr} \\
    --output-model-id ufc-v1

# 5. Статус
firectl get fine-tuning-job ufc-v1
"""

            st.code(cmd, language="bash")
            st.download_button(
                "⬇️ Скачать команды",
                data=cmd.encode("utf-8"),
                file_name=f"finetune_{platform.lower().replace('.','_')}.sh",
                mime="text/x-shellscript",
            )

    # =====================================================================
    # TAB: JOBS
    # =====================================================================
    with tab_jobs:
        st.markdown("### 🚀 Активные / завершённые jobs (OpenAI)")
        jobs = st.session_state.get("ft_jobs", [])
        if not jobs:
            st.info("Jobs пока нет. Запусти OpenAI fine-tuning во вкладке Train.")
        else:
            api_key_ft = st.session_state.get("api_key_input", "")
            for j in jobs:
                with st.expander(f"📦 {j.get('id')} · {j.get('base_model')} · {j.get('status','?')}"):
                    st.json(j)
                    if st.button("🔄 Обновить статус", key=f"refresh_{j['id']}"):
                        if not api_key_ft:
                            st.error("API Key нужен.")
                        else:
                            try:
                                upd = openai_get_finetune_status(api_key_ft, j["id"])
                                j["status"] = upd.get("status", "?")
                                j["fine_tuned_model"] = upd.get("fine_tuned_model")
                                st.session_state.ft_jobs = jobs
                                st.json(upd)
                                if upd.get("fine_tuned_model"):
                                    st.success(
                                        f"🎉 Готово! Модель: `{upd['fine_tuned_model']}`"
                                    )
                                    if st.button("➕ Зарегистрировать в Custom Models",
                                                 key=f"reg_{j['id']}"):
                                        register_custom_model({
                                            "name": f"UFC {j.get('suffix','v1')}",
                                            "provider": "openai",
                                            "model_id": upd["fine_tuned_model"],
                                            "base_model": j.get("base_model"),
                                            "created_at": datetime.now().isoformat(),
                                            "notes": f"Job {j['id']}",
                                        })
                                        st.toast("✅ Зарегистрирована.")
                                        st.rerun()
                            except Exception as e:
                                st.error(f"Ошибка: {e}")

    # =====================================================================
    # TAB: CUSTOM MODELS
    # =====================================================================
    with tab_models:
        st.markdown("### 🎯 Реестр кастомных моделей")
        st.caption("Эти модели появятся в сайдбаре в выпадашке выбора LLM.")

        models = list_custom_models()
        if not models:
            st.info("Пока пусто. Завершённый OpenAI job можно зарегистрировать "
                    "из вкладки Jobs. Или добавь вручную ниже.")
        else:
            df = pd.DataFrame(models)
            st.dataframe(df, use_container_width=True, hide_index=True)
            for m in models:
                if st.button(f"🗑️ Удалить {m['name']}",
                             key=f"rm_{m['model_id']}"):
                    remove_custom_model(m["model_id"])
                    st.rerun()

        st.markdown("---")
        st.markdown("#### ➕ Добавить вручную")
        with st.form("add_custom_model"):
            mc1, mc2 = st.columns(2)
            mname = mc1.text_input("Имя", "")
            mprov = mc2.selectbox("Провайдер",
                ["openai", "together", "fireworks", "huggingface", "local"])
            mid = st.text_input(
                "Model ID *",
                placeholder="ft:gpt-4o-mini:user:ufc-v1:abc или путь к LoRA",
            )
            base = st.text_input("Базовая модель", "")
            notes = st.text_area("Заметки", "", height=80)
            if st.form_submit_button("✅ Добавить", use_container_width=True):
                if not mid:
                    st.error("Model ID обязателен.")
                else:
                    register_custom_model({
                        "name": mname or mid,
                        "provider": mprov,
                        "model_id": mid,
                        "base_model": base,
                        "created_at": datetime.now().isoformat(),
                        "notes": notes,
                    })
                    st.success("Добавлено.")
                    st.rerun()

    # =====================================================================
    # TAB: HELP
    # =====================================================================
    with tab_help:
        st.markdown("### ❓ Гайд по fine-tuning")
        st.markdown("""
#### Что вообще даёт fine-tuning?
- **Точность**: модель учится на твоих исходах вместо генерики из базы знаний
- **Формат**: гарантированно структурированный output без drift'а
- **Стоимость**: маленькая ft-модель часто дешевле большой при равном качестве
- **Кастом-стиль**: твой sharp MMA-tone закрепляется в весах

#### Когда стоит делать FT?
| Условие | Ответ |
|---|---|
| Меньше 50 примеров | НЕТ — мало данных |
| 50-200 примеров | ⚠️ Стоит попробовать только OpenAI/Together (cloud) |
| 200+ примеров | ✅ Имеет смысл LoRA |
| 1000+ примеров | 🚀 Полная мощь — пробуй разные base models |

#### Какой провайдер выбрать?
- **OpenAI** — проще всего, дороже, лучшее качество базы.
- **Together.ai** — дёшево + Llama/Qwen base, хорошо для Pro tier.
- **LoRA локально** — Колаб бесплатный, но требует базовых ML знаний.

#### Как использовать ft-модель в приложении?
1. Завершишь обучение → зарегистрируй в **Custom Models** (или добавь вручную).
2. В сайдбаре в выпадашке моделей выбери свою кастомную.
3. Все прогнозы пойдут через неё.

#### Continual learning
Каждые 2-4 недели: пересобери датасет (новые резолвнутые прогнозы попадают автоматически)
→ обучи новую версию (`ufc-v2`, `ufc-v3`...) → сравни Brier Score со старой версией
на странице **History & Accuracy**.

#### Структура training-примера
```json
{
  "messages": [
    {"role": "system", "content": "You are an elite UFC fight analyst..."},
    {"role": "user", "content": "Дай прогноз на бой UFC. ИВЕНТ: ... БОЙ: A vs B"},
    {"role": "assistant", "content": "### 🎯 ПРОГНОЗ\\nПобедитель: **A** — 75%..."}
  ]
}
```

#### Best practices
- Минимум 80% примеров должны быть **резолвнутыми** прогнозами с реальными исходами
- Балансируй классы: не все примеры должны быть «фаворит выиграл»
- Включай **апсеты** для калибровки уверенности
- Обновляй каждые 50-100 новых примеров
""")
