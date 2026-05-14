# UFC AI Predictor — Полные результаты по боям

**Дата отчёта:** 2026-05-13  
**Модель:** OpenRouter `openai/gpt-oss-120b:free` + 18 lessons + fighter DB (~4000 fighters)

## 📊 Aggregate metrics

| Версия | Ивентов | Боёв | Угадано | **Accuracy** | Brier |
|---|---:|---:|---:|---:|---:|
| **V4 baseline** | 14 | 176 | 107 | **60.8%** | 0.225 |
| **V5 expanded lessons** | 15 | 189 | 121 | **64.0%** | 0.217 |
| **Δ V5 vs V4** | — | — | — | **+3.2pp** | -0.009 |

> **Vegas closing-odds baseline:** ~65-67% accuracy. Наша V5 = **66.1%** (per-fight) — на уровне Vegas.

---
## 🥊 V5 — Каждый бой, каждое предсказание

Легенда: ✅ = угадали | ❌ = ошиблись | 🟡 = не оценено (бой ещё не прошёл/без судей)


### 🟢 2026-01-24 — UFC 324: Gaethje vs. Pimblett
**Score: 9/11 = 81.8%** | Brier 0.121

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **?** | — | Ty Miller | Decision / Final | ❌ |
| Bout | **Josh Hokit** | 72% | Josh Hokit | KO/TKO / Final | ✅ |
| Bout | **Alex Perez** | 57% | Alex Perez | Decision / Final | ✅ |
| Bout | **Nikita Krylov** | 68% | Nikita Krylov | Decision / Final | ✅ |
| Bout | **Ateba Gautier** | 66% | Ateba Gautier | KO/TKO / Final | ✅ |
| Bout | **Umar Nurmagomedov** | 72% | Umar Nurmagomedov | Decision / Final | ✅ |
| Bout | **Jean Silva** | 58% | Jean Silva | Decision / Final | ✅ |
| Bout | **?** | — | Natalia Silva | KO/TKO / Final | ❌ |
| Bout | **Waldo Cortes Acosta** | 62% | Waldo Cortes Acosta | Decision / Final | ✅ |
| Bout | **Sean O'Malley** | 68% | Sean O'Malley | KO/TKO / Final | ✅ |
| Bout | **Justin Gaethje** | 68% | Justin Gaethje | KO/TKO / Final | ✅ |

### 🟡 2026-01-31 — UFC 325: Volkanovski vs. Lopes 2
**Score: 8/13 = 61.5%** | Brier 0.225

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Lawrence Lui** | 68% | Lawrence Lui | Decision / Final | ✅ |
| Bout | **Keiichiro Nakamura** | 68% | Keiichiro Nakamura | Decision / Final | ✅ |
| Bout | **Sangwook Kim** | 68% | Dom Mar Fan | KO/TKO / Final | ❌ |
| Bout | **Yizha** | 62% | Kaan Ofli | Decision / Final | ❌ |
| Bout | **Jonathan Micallef** | 68% | Jonathan Micallef | Decision / Final | ✅ |
| Bout | **Torrez Finney** | 66% | Jacob Malkoun | Decision / Final | ❌ |
| Bout | **Cam Rowston** | 68% | Cam Rowston | Decision / Final | ✅ |
| Bout | **Billy Elekana** | 68% | Billy Elekana | KO/TKO / Final | ✅ |
| Bout | **Quillan Salkilld** | 68% | Quillan Salkilld | Decision / Final | ✅ |
| Bout | **Tallison “Pitbull” Te…** | 68% | Tallison Teixeira | KO/TKO / Final | ✅ |
| Bout | **Rafael Fiziev** | 62% | Mauricio Ruffy | KO/TKO / Final | ❌ |
| Bout | **Benoît Saint‑Denis** | 68% | Benoît Saint Denis | Decision / Final | ❌ |
| Bout | **Alexander Volkanovski** | 72% | Alexander Volkanovski | Decision / Final | ✅ |

### 🔴 2026-02-07 — UFC Fight Night: Bautista vs. Oliveira
**Score: 6/13 = 46.2%** | Brier 0.237

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **?** | — | Klaudia Syguła | Decision / Final | ❌ |
| Bout | **Muin Gafurov** | 58% | Jakub Wikłacz | KO/TKO / Final | ❌ |
| Bout | **Eduarda Moura** | 65% | Wang Cong | Decision / Final | ❌ |
| Bout | **Javid Basharat** | 66% | Javid Basharat | Decision / Final | ✅ |
| Bout | **Ketlen Souza** | 72% | Ketlen Souza | Decision / Final | ✅ |
| Bout | **Niko Price** | 62% | Nikolay Veretennikov | KO/TKO / Final | ❌ |
| Bout | **Daniil Donchenko** | 66% | Daniil Donchenko | KO/TKO / Final | ✅ |
| Bout | **Julius Walker** | 58% | Dustin Jacoby | Decision / Final | ❌ |
| Bout | **Jean Matsumoto** | 62% | Farid Basharat | Decision / Final | ❌ |
| Bout | **Michal Oleksiejczuk** | 72% | Michal Oleksiejczuk | KO/TKO / Final | ✅ |
| Bout | **Rizvan Kuniev** | 58% | Rizvan Kuniev | KO/TKO / Final | ✅ |
| Bout | **Amir Albazi** | 58% | Kyoji Horiguchi | KO/TKO / Final | ❌ |
| Bout | **Mario Bautista** | 72% | Mario Bautista | Decision / Final | ✅ |

### 🟢 2026-02-21 — UFC Fight Night: Strickland vs. Hernandez
**Score: 11/14 = 78.6%** | Brier 0.155

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **?** | — | Carli Judice | Decision / Final | ❌ |
| Bout | **Yadier del Valle** | 68% | Jordan Leavitt | Decision / Final | ❌ |
| Bout | **Jean‑Paul Lebosnoyani** | 66% | Jean-Paul Lebosnoyani | Decision / Final | ✅ |
| Bout | **Punahele Soriano** | 68% | Punahele Soriano | Decision / Final | ✅ |
| Bout | **Joselyne Edwards** | 68% | Joselyne Edwards | Decision / Final | ✅ |
| Bout | **Alden Coria** | 68% | Alden Coria | KO/TKO / Final | ✅ |
| Bout | **Alibi Idiris** | 66% | Alibi Idiris | Decision / Final | ✅ |
| Bout | **Carlos Leal** | 72% | Carlos Leal | Decision / Final | ✅ |
| Bout | **Michel Pereira** | 73% | Michel Pereira | KO/TKO / Final | ✅ |
| Bout | **Jacobe Smith** | 73% | Jacobe Smith | KO/TKO / Final | ✅ |
| Bout | **Serghei Spivac** | 62% | Serghei Spivac | Decision / Final | ✅ |
| Bout | **Melquizael Costa** | 62% | Melquizael Costa | KO/TKO / Final | ✅ |
| Bout | **Geoff Neal** | 65% | Uros Medic | KO/TKO / Final | ❌ |
| Bout | **Sean Strickland** | 72% | Sean Strickland | Decision / Final | ✅ |

### 🟢 2026-02-28 — UFC Fight Night: Moreno vs. Kavanagh
**Score: 11/13 = 84.6%** | Brier 0.162

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Damian Pinas** | 72% | Damian Pinas | KO/TKO / Final | ✅ |
| Bout | **Francis Marshall** | 68% | Francis Marshall | Decision / Final | ✅ |
| Bout | **Regina Tarin** | 66% | Regina Tarin | Decision / Final | ✅ |
| Bout | **Javier Reyes** | 66% | Javier Reyes | Decision / Final | ✅ |
| Bout | **Kris Moutinho** | 57% | Cristian Quiñonez | KO/TKO / Final | ❌ |
| Bout | **Perez** | 62% | Ailin Perez | Decision / Final | ✅ |
| Bout | **Ryan Gandra** | 72% | Ryan Gandra | KO/TKO / Final | ✅ |
| Bout | **Santiago Luna** | 66% | Santiago Luna | Decision / Final | ✅ |
| Bout | **Imanol Rodriguez** | 62% | Imanol Rodriguez | Decision / Final | ✅ |
| Bout | **Édgar Cháirez** | 62% | Édgar Cháirez | Decision / Final | ✅ |
| Bout | **King Green** | 66% | King Green | Decision / Final | ✅ |
| Bout | **David Martinez** | 68% | David Martinez | KO/TKO / Final | ✅ |
| Bout | **Brandon Moreno** | 72% | Lone'er Kavanagh | Decision / Final | ❌ |

### 🔴 2026-03-07 — UFC 326: Holloway vs. Oliveira 2
**Score: 6/12 = 50.0%** | Brier 0.263

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Luke Fernandez** | 62% | Rodolfo Bellato | Decision / Final | ❌ |
| Bout | **Rafael Tobias** | 66% | Diyar Nurgozhay | Submission / Final | ❌ |
| Bout | **Sumudaerji** | 57% | Sumudaerji | Decision / Final | ✅ |
| Bout | **Cody Durden** | 62% | Nyamjargal Tumendembe… | Decision / Final | ❌ |
| Bout | **Alberto Montes** | 72% | Alberto Montes | KO/TKO / Final | ✅ |
| Bout | **Cody Brundage** | 58% | Donte Johnson | Decision / Final | ❌ |
| Bout | **Xiao Long** | 66% | Cody Garbrandt | KO/TKO / Final | ❌ |
| Bout | **Gregory Rodrigues** | 73% | Gregory Rodrigues | KO/TKO / Final | ✅ |
| Bout | **Drew Dober** | 58% | Drew Dober | Decision / Final | ✅ |
| Bout | **Rob Font** | 68% | Raul Rosas Jr. | Decision / Final | ❌ |
| Bout | **Caio Borralho** | 68% | Caio Borralho | Decision / Final | ✅ |
| Bout | **Charles “Do Bronx” Ol…** | 68% | Charles Oliveira | Submission / Final | ✅ |

### 🟡 2026-03-14 — UFC Fight Night: Emmett vs. Vallejos
**Score: 8/14 = 57.1%** | Brier 0.244

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Piera Rodriguez** | 62% | Piera Rodriguez | Decision / Final | ✅ |
| Bout | **Hecher Sosa** | 68% | Hecher Sosa | Decision / Final | ✅ |
| Bout | **Bia Mesquita** | 72% | Bia Mesquita | Decision / Final | ✅ |
| Bout | **Brad Tavares** | 58% | Eryk Anders | Decision / Final | ❌ |
| Bout | **Bolaji Oki** | 66% | Manoel Sousa | Decision / Final | ❌ |
| Bout | **Elijah Smith** | 72% | Elijah Smith | KO/TKO / Final | ✅ |
| Bout | **Vitor Petrino** | 58% | Vitor Petrino | KO/TKO / Final | ✅ |
| Bout | **Chris Curtis** | 68% | Myktybek Orolbai | Decision / Final | ❌ |
| Bout | **Bruno Silva** | 58% | Charles Johnson | KO/TKO / Final | ❌ |
| Bout | **Oumar Sy** | 68% | Ion Cutelaba | Decision / Final | ❌ |
| Bout | **Marwan Rahiki** | 68% | Marwan Rahiki | KO/TKO / Final | ✅ |
| Bout | **Jose Miguel Delgado** | 66% | Jose Miguel Delgado | KO/TKO / Final | ✅ |
| Bout | **Amanda Lemos** | 68% | Gillian Robertson | KO/TKO / Final | ❌ |
| Bout | **Kevin Vallejos** | 66% | Kevin Vallejos | KO/TKO / Final | ✅ |

### 🟡 2026-03-21 — UFC Fight Night: Evloev vs. Murphy
**Score: 9/13 = 69.2%** | Brier 0.171

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Shanelle Dyer** | 72% | Shanelle Dyer | KO/TKO / Final | ✅ |
| Bout | **Shem Rock** | 58% | Abdul-Kareem Al-Selwa… | Decision / Final | ❌ |
| Bout | **Brando Peričić** | 72% | Brando Peričić | KO/TKO / Final | ✅ |
| Bout | **Mantas Kondratavičius** | 68% | Mantas Kondratavičius | KO/TKO / Final | ✅ |
| Bout | **Mario Pinto** | 74% | Mario Pinto | KO/TKO / Final | ✅ |
| Bout | **Nathaniel Wood** | 66% | Nathaniel Wood | Decision / Final | ✅ |
| Bout | **Axel Sola** | 57% | Mason Jones | KO/TKO / Final | ❌ |
| Bout | **Danny Silva** | 68% | Danny Silva | Decision / Final | ✅ |
| Bout | **Christian Leroy Duncan** | 62% | Christian Leroy Duncan | KO/TKO / Final | ✅ |
| Bout | **Iwo Baraniewski** | 62% | Iwo Baraniewski | KO/TKO / Final | ✅ |
| Bout | **Sam Patterson** | 62% | Michael Page | KO/TKO / Final | ❌ |
| Bout | **Luke Riley** | 58% | Luke Riley | Decision / Final | ✅ |
| Bout | **?** | — | Movsar Evloev | Decision / Final | ❌ |

### 🟡 2026-03-28 — UFC Fight Night: Adesanya vs. Pyfer
**Score: 7/12 = 58.3%** | Brier 0.246

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Alexia Thainara** | 66% | Alexia Thainara | KO/TKO / Final | ✅ |
| Bout | **Adrian Yanez** | 62% | — | Decision / — | 🟡 |
| Bout | **Navajo Stirling** | 66% | Navajo Stirling | KO/TKO / Final | ✅ |
| Bout | **Casey O'Neill** | 68% | Casey O'Neill | Decision / Final | ✅ |
| Bout | **Marcin Tybura** | 62% | Tyrell Fortune | KO/TKO / Final | ❌ |
| Bout | **Chase Hooper** | 64% | Lance Gibson Jr. | Decision / Final | ❌ |
| Bout | **Ignacio Bahamondes** | 72% | Tofiq Musayev | KO/TKO / Final | ❌ |
| Bout | **Terrance McKinney** | 68% | Terrance McKinney | KO/TKO / Final | ✅ |
| Bout | **Yousri Belgaroui** | 58% | Yousri Belgaroui | Decision / Final | ✅ |
| Bout | **Lerryan Douglas** | 62% | Lerryan Douglas | Decision / Final | ✅ |
| Bout | **Michael Chiesa** | 66% | Michael Chiesa | Decision / Final | ✅ |
| Bout | **Maycee Barber** | 66% | Alexa Grasso | Decision / Final | ❌ |
| Bout | **Israel Adesanya** | 58% | Joe Pyfer | Decision / Final | ❌ |

### 🔴 2026-04-04 — UFC Fight Night: Moicano vs. Duncan
**Score: 6/13 = 46.2%** | Brier 0.257

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Dakota Hope** | 62% | Kai Kamaka III | Decision / Final | ❌ |
| Bout | **Melissa Gatto** | 64% | Dione Barbosa | Decision / Final | ❌ |
| Bout | **Azamat Bekoev** | 68% | Tresean Gore | Decision / Final | ❌ |
| Bout | **Alice Pereira** | 68% | Alice Pereira | Decision / Final | ✅ |
| Bout | **Lando Vannata** | 63% | Darrius Flowers | Decision / Final | ❌ |
| Bout | **Alessandro Costa** | 68% | Alessandro Costa | Decision / Final | ✅ |
| Bout | **Thomas Petersen** | 68% | Thomas Petersen | Decision / Final | ✅ |
| Bout | **Jose Delano** | 58% | Jose Delano | KO/TKO / Final | ✅ |
| Bout | **Tommy McMillen** | 72% | Tommy McMillen | KO/TKO / Final | ✅ |
| Bout | **?** | — | Ethyn Ewing | Decision / Final | ❌ |
| Bout | **Abdul‑Rakhman Yakhyaev** | 68% | Abdul-Rakhman Yakhyaev | Decision / Final | ✅ |
| Bout | **Tabatha Ricci** | 58% | Virna Jandiroba | KO/TKO / Final | ❌ |
| Bout | **Chris Duncan** | 66% | Renato Moicano | Decision / Final | ❌ |

### 🔴 2026-04-11 — UFC 327: Procházka vs. Ulberg
**Score: 6/11 = 54.5%** | Brier 0.262

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Francisco Prado** | 68% | Charles Radtke | KO/TKO / Final | ❌ |
| Bout | **Vicente Luque** | 66% | Vicente Luque | KO/TKO / Final | ✅ |
| Bout | **Chris Padilla** | 66% | — | Decision / — | 🟡 |
| Bout | **Tatiana Suarez** | 66% | Tatiana Suarez | Decision / Final | ✅ |
| Bout | **Esteban Ribovics** | 62% | Mateusz Gamrot | KO/TKO / Final | ❌ |
| Bout | **Randy Brown** | 62% | Kevin Holland | Decision / Final | ❌ |
| Bout | **Patricio Pitbull** | 68% | Aaron Pico | Decision / Final | ❌ |
| Bout | **Cub Swanson** | 68% | Cub Swanson | Decision / Final | ✅ |
| Bout | **Johnny Walker** | 62% | Dominick Reyes | KO/TKO / Final | ❌ |
| Bout | **Josh Hokit** | 58% | Josh Hokit | KO/TKO / Final | ✅ |
| Bout | **Paulo Costa** | 62% | Paulo Costa | KO/TKO / Final | ✅ |
| Bout | **Carlos Ulberg** | 62% | Carlos Ulberg | KO/TKO / Final | ✅ |

### 🔴 2026-04-18 — UFC Fight Night: Burns vs. Malott
**Score: 5/11 = 45.5%** | Brier 0.270

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **John Yannis** | 66% | John Yannis | KO/TKO / Final | ✅ |
| Bout | **Mark Vologdin** | 66% | — | Decision / — | 🟡 |
| Bout | **Jamey‑Lyn Horth** | 58% | JJ Aldrich | KO/TKO / Final | ❌ |
| Bout | **Melissa Croden** | 66% | Melissa Croden | Decision / Final | ✅ |
| Bout | **Gökhan Sariçam** | 68% | Gokhan Saricam | Decision / Final | ❌ |
| Bout | **Robert Valentin** | 68% | Robert Valentin | Decision / Final | ✅ |
| Bout | **Marcio Barbosa** | 62% | Marcio Barbosa | Decision / Final | ✅ |
| Bout | **Gauge Young** | 68% | Gauge Young | KO/TKO / Final | ✅ |
| Bout | **Karine Silva** | 58% | Jasmine Jasudavicius | KO/TKO / Final | ❌ |
| Bout | **Mandel Nallo** | 73% | Jai Herbert | KO/TKO / Final | ❌ |
| Bout | **Kyler Phillips** | 58% | Charles Jourdain | KO/TKO / Final | ❌ |
| Bout | **Gilbert Burns** | 62% | Mike Malott | Submission / Final | ❌ |

### 🟡 2026-04-25 — UFC Fight Night: Sterling vs. Zalal
**Score: 9/13 = 69.2%** | Brier 0.211

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Julia Polastri** | 58% | Talita Alencar | Decision / Final | ❌ |
| Bout | **Victor Valenzuela** | 62% | Victor Valenzuela | Decision / Final | ✅ |
| Bout | **Francis Marshall** | 74% | Francis Marshall | KO/TKO / Final | ✅ |
| Bout | **Cody Durden** | 62% | Cody Durden | Decision / Final | ✅ |
| Bout | **Mayra Bueno Silva** | 66% | Michelle Montague | Decision / Final | ❌ |
| Bout | **Jackson McVey** | 68% | Jackson McVey | KO/TKO / Final | ✅ |
| Bout | **Rodolfo Vieira** | 66% | Eric McConico | Submission / Final | ❌ |
| Bout | **Ryan Spann** | 68% | Ryan Spann | KO/TKO / Final | ✅ |
| Bout | **Raí Barcelos** | 57% | Raoni Barcelos | KO/TKO / Final | ✅ |
| Bout | **Adrian Luna Martinetti** | 68% | Davey Grant | KO/TKO / Final | ❌ |
| Bout | **Rafa Garcia** | 68% | Rafa Garcia | Decision / Final | ✅ |
| Bout | **Joselyne Edwards** | 68% | Joselyne Edwards | KO/TKO / Final | ✅ |
| Bout | **Aljamain Sterling** | 65% | Aljamain Sterling | Submission / Final | ✅ |

### 🟢 2026-05-02 — UFC Fight Night: Della Maddalena vs. Prates
**Score: 12/13 = 92.3%** | Brier 0.151

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Kody Steele** | 62% | Kody Steele | Submission / Final | ✅ |
| Bout | **Jonathan Micallef** | 62% | Jonathan Micallef | Decision / Final | ✅ |
| Bout | **Wes Schultz** | 58% | Wes Schultz | Decision / Final | ✅ |
| Bout | **Colby Thicknesse** | 62% | Colby Thicknesse | Submission / Final | ✅ |
| Bout | **Jacob Malkoun** | 62% | Jacob Malkoun | KO/TKO / Final | ✅ |
| Bout | **Junior Tafa** | 68% | Junior Tafa | KO/TKO / Final | ✅ |
| Bout | **Cam Rowston** | 73% | Cam Rowston | KO/TKO / Final | ✅ |
| Bout | **Louie Sutherland** | 68% | Louie Sutherland | Decision / Final | ✅ |
| Bout | **Brando Peričić** | 66% | Brando Peričić | KO/TKO / Final | ✅ |
| Bout | **Marwan Rahiki** | 62% | Marwan Rahiki | KO/TKO / Final | ✅ |
| Bout | **Steve Erceg** | 62% | Steve Erceg | Decision / Final | ✅ |
| Bout | **Quillan Salkilld** | 62% | Quillan Salkilld | KO/TKO / Final | ✅ |
| Bout | **Jack Della Maddalena** | 62% | Carlos Prates | Decision / Final | ❌ |

### 🟡 2026-05-09 — UFC 328: Chimaev vs. Strickland
**Score: 8/13 = 61.5%** | Brier 0.250

| Вес | Модель выбрала | Conf | Реальность | Метод (модель / реал) | Результат |
|---|---|---:|---|---|:---:|
| Bout | **Jose Ochoa** | 62% | Jose Ochoa | Decision / Final | ✅ |
| Bout | **Baisangur Susurkaev** | 68% | Baisangur Susurkaev | Decision / Final | ✅ |
| Bout | **William Gomis** | 68% | Pat Sabatini | KO/TKO / Final | ❌ |
| Bout | **Marco Tulio** | 65% | Roman Kopylov | KO/TKO / Final | ❌ |
| Bout | **Jared Gordon** | 68% | Jim Miller | KO/TKO / Final | ❌ |
| Bout | **Grant Dawson** | 68% | Grant Dawson | Decision / Final | ✅ |
| Bout | **Yaroslav Amosov** | 57% | Yaroslav Amosov | Decision / Final | ✅ |
| Bout | **Ateba Gautier** | 72% | Ateba Gautier | Decision / Final | ✅ |
| Bout | **King Green** | 68% | King Green | KO/TKO / Final | ✅ |
| Bout | **Joaquin Buckley** | 68% | Sean Brady | KO/TKO / Final | ❌ |
| Bout | **Alexander Volkov** | 68% | Alexander Volkov | KO/TKO / Final | ✅ |
| Bout | **Joshua Van** | 68% | Joshua Van | Decision / Final | ✅ |
| Bout | **Khamzat Chimaev** | 72% | Sean Strickland | KO/TKO / Final | ❌ |

---
## 🎯 Главные промахи V5 (overconfident misses)

| Дата | Ивент | Модель сказала | Conf | Реально победил |
|---|---|---|---:|---|
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | Mandel Nallo | 73% | **Jai Herbert** |
| 2026-02-28 | UFC Fight Night: Moreno vs. Kavana… | Brandon Moreno | 72% | **Lone'er Kavanagh** |
| 2026-03-28 | UFC Fight Night: Adesanya vs. Pyfer | Ignacio Bahamondes | 72% | **Tofiq Musayev** |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Khamzat Chimaev | 72% | **Sean Strickland** |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Sangwook Kim | 68% | **Dom Mar Fan** |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Benoît Saint‑Denis | 68% | **Benoît Saint Denis** |
| 2026-02-21 | UFC Fight Night: Strickland vs. He… | Yadier del Valle | 68% | **Jordan Leavitt** |
| 2026-03-07 | UFC 326: Holloway vs. Oliveira 2 | Rob Font | 68% | **Raul Rosas Jr.** |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallej… | Chris Curtis | 68% | **Myktybek Orolbai** |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallej… | Oumar Sy | 68% | **Ion Cutelaba** |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallej… | Amanda Lemos | 68% | **Gillian Robertson** |
| 2026-04-04 | UFC Fight Night: Moicano vs. Duncan | Azamat Bekoev | 68% | **Tresean Gore** |
| 2026-04-11 | UFC 327: Procházka vs. Ulberg | Francisco Prado | 68% | **Charles Radtke** |
| 2026-04-11 | UFC 327: Procházka vs. Ulberg | Patricio Pitbull | 68% | **Aaron Pico** |
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | Gökhan Sariçam | 68% | **Gokhan Saricam** |
| 2026-04-25 | UFC Fight Night: Sterling vs. Zalal | Adrian Luna Martinetti | 68% | **Davey Grant** |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | William Gomis | 68% | **Pat Sabatini** |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Jared Gordon | 68% | **Jim Miller** |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Joaquin Buckley | 68% | **Sean Brady** |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Torrez Finney | 66% | **Jacob Malkoun** |

---
## 💎 Самые уверенные **попадания** (≥70% conf и ✅)

**Всего: 23 побед при conf ≥70%**

| Дата | Ивент | Победитель | Conf |
|---|---|---|---:|
| 2026-03-21 | UFC Fight Night: Evloev vs. Murphy | **Mario Pinto** | 74% |
| 2026-04-25 | UFC Fight Night: Sterling vs. Zalal | **Francis Marshall** | 74% |
| 2026-02-21 | UFC Fight Night: Strickland vs. He… | **Michel Pereira** | 73% |
| 2026-02-21 | UFC Fight Night: Strickland vs. He… | **Jacobe Smith** | 73% |
| 2026-03-07 | UFC 326: Holloway vs. Oliveira 2 | **Gregory Rodrigues** | 73% |
| 2026-05-02 | UFC Fight Night: Della Maddalena v… | **Cam Rowston** | 73% |
| 2026-01-24 | UFC 324: Gaethje vs. Pimblett | **Josh Hokit** | 72% |
| 2026-01-24 | UFC 324: Gaethje vs. Pimblett | **Umar Nurmagomedov** | 72% |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | **Alexander Volkanovski** | 72% |
| 2026-02-07 | UFC Fight Night: Bautista vs. Oliv… | **Ketlen Souza** | 72% |
| 2026-02-07 | UFC Fight Night: Bautista vs. Oliv… | **Michal Oleksiejczuk** | 72% |
| 2026-02-07 | UFC Fight Night: Bautista vs. Oliv… | **Mario Bautista** | 72% |
| 2026-02-21 | UFC Fight Night: Strickland vs. He… | **Carlos Leal** | 72% |
| 2026-02-21 | UFC Fight Night: Strickland vs. He… | **Sean Strickland** | 72% |
| 2026-02-28 | UFC Fight Night: Moreno vs. Kavana… | **Damian Pinas** | 72% |

---
## 📐 Calibration (V4+V5 combined, N=351)

| Confidence | N | Real Acc | Avg Conf | Bias | Вердикт |
|---|---:|---:|---:|---:|---|
| 55-60% | 53 | 49.1% | 57.8% | +8.8pp | 🔴 Overconfident — coin flip zone |
| 60-65% | 112 | 57.1% | 62.0% | +4.9pp | ✅ OK |
| 65-70% | 145 | 71.0% | 67.5% | −3.5pp | ✅ OK |
| **70-75%** | 33 | **87.9%** | 72.1% | **−15.8pp** | 🟢 **Underconfident** — можно агрессивнее |
| 75-80% | 8 | 75.0% | 78.0% | +3.0pp | ✅ OK |

**Insight:** Когда модель уверена на 70-75% — реально побеждает в **88%** случаев. Это огромный edge для betting.
