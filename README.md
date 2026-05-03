# 🔨 LocalForge

**Yerel LLM ile otomatik proje geliştirme ajanı.**

Sisteminizi tarar, donanımınıza uygun modeli önerir, projenizi sıfırdan planlar ve kodlar. Tüm işlem yerel — hiçbir şey buluta gitmez.

---

## ✨ Özellikler

- 🖥️ **Sistem Tarayıcı** — GPU, VRAM, RAM otomatik tespit. Ollama ve LM Studio bağlantı kontrolü.
- 🤖 **Çift Model Stratejisi** — Planlama için akıllı model, kodlama için hızlı model. İkisini ayrı seçebilirsin.
- 📋 **Otomatik Planlama** — Projenin mimarisini ve görev listesini ajan kendisi oluşturur.
- ⚡ **Otomatik & Onay Modu** — Ajan tamamen kendi başına ilerler ya da her adımda senden onay alır.
- 🧠 **Token-Safe Bağlam** — MD dosyası tabanlı hafıza sistemi. Bağlam sıfırlansa bile kaldığı yerden devam eder.
- ✅ **Syntax Doğrulama** — Üretilen kod otomatik kontrol edilir, hata varsa LLM'e geri gönderilir.
- 📦 **Bağımlılık Tespiti** — Import'lar taranır, `requirements.txt` otomatik güncellenir.
- ⏪ **Checkpoint / Rollback** — Her görev sonrası snapshot alınır. İstediğin noktaya tek tıkla geri dön.
- 🏗️ **Opsiyonel Şablonlar** — FastAPI, React, Next.js, CLI için hazır iskeletler. Zorunlu değil, sadece öneri.
- 🌐 **Streamlit Web UI** — Görev takibi, canlı kod önizleme, diff görünümü, checkpoint geçmişi.

---

## 🖥️ Desteklenen Donanım

| GPU | Önerilen Model |
|-----|---------------|
| NVIDIA 4GB VRAM | Qwen2.5 3B / Phi-3 Mini |
| NVIDIA 8GB VRAM | Qwen2.5-Coder 7B ⭐ |
| NVIDIA 12GB+ VRAM | DeepSeek-Coder V2 16B |
| Apple Silicon | Qwen2.5 7B (Unified Memory) |
| GPU yok (CPU) | Phi-3 Mini |

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/onrart/LocalForge.git
cd LocalForge

# 2. Kurulumu çalıştır (bağımlılıkları otomatik kurar)
python setup.py

# 3. Başlat
streamlit run app.py
```

> **Gereksinimler:** Python 3.10+ ve [Ollama](https://ollama.ai) veya [LM Studio](https://lmstudio.ai) kurulu olmalı.

---

## 🔌 Desteklenen Backend'ler

| | Ollama | LM Studio |
|--|--------|-----------|
| Varsayılan Port | 11434 | 1234 |
| API | OpenAI-uyumlu | OpenAI-uyumlu |
| Streaming | ✅ | ✅ |
| Özel Port | ✅ | ✅ |

---

## 📁 Proje Yapısı

```
LocalForge/
├── app.py                        # Streamlit giriş noktası
├── setup.py                      # Otomatik kurulum (bağımlılık + klasör)
├── requirements.txt              # Python bağımlılıkları
├── config.json                   # Kullanıcı tercihleri (gitignore'da)
│
├── core/
│   ├── system_scanner.py         # GPU/RAM/OS tespiti, backend ping
│   ├── llm_recommender.py        # VRAM'e göre model önerisi
│   ├── llm_client.py             # Ollama / LM Studio API sarmalayıcısı
│   ├── context_manager.py        # .agent/ MD dosyaları, checkpoint, memory
│   ├── requirements_collector.py # Proje istemi formu ve şablon tespiti
│   ├── syntax_validator.py       # Python/JS/TS/JSON doğrulama + fix prompt
│   ├── dependency_scanner.py     # Import tarayıcı → requirements.txt
│   ├── file_writer.py            # Atomic yazma, diff üretimi, LLM parse
│   └── template_manager.py       # Şablon uygulama ve placeholder doldurma
│
├── agents/
│   ├── planner_agent.py          # ARCHITECTURE.md + TASKS.md üretir
│   ├── coder_agent.py            # Görev döngüsü, retry, onay modu
│   └── editor_agent.py           # Hedefli düzenleme, diff, MEMORY sync
│
├── prompts/
│   ├── planner.md                # Planlayıcı sistem promptu
│   ├── coder.md                  # Kodlayıcı sistem promptu
│   └── editor.md                 # Düzenleyici sistem promptu
│
├── templates/
│   ├── _registry.json            # Stack → şablon eşleştirme
│   ├── fastapi/                  # FastAPI + SQLAlchemy + Pydantic iskeleti
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── config.py
│   │       └── database.py
│   ├── react/                    # React + Vite + TypeScript iskeleti
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       └── App.tsx
│   ├── nextjs/                   # Next.js 14 + App Router iskeleti
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   └── app/
│   │       ├── layout.tsx
│   │       └── page.tsx
│   └── cli/                      # Python CLI + Click + Rich iskeleti
│       ├── main.py
│       ├── requirements.txt
│       └── src/
│           ├── cli.py
│           └── config.py
│
└── ui/
    └── pages/
        ├── 1_setup.py            # Sistem tarama + model seçimi
        ├── 2_requirements.py     # Proje istemi + planlama
        ├── 3_workspace.py        # Kodlama + canlı takip + checkpoint
        └── 4_editor.py           # LLM ile düzenleme + direkt edit
```

---

## 🧠 Nasıl Çalışır?

LocalForge, token limitine takılmamak için tüm "hafızayı" MD dosyalarında tutar. Her LLM çağrısında projenin tamamı değil, yalnızca o an için gereken bilgi gönderilir (~2200 token):

```
PROJECT.md        → Proje adı, stack, hedef
CURRENT_TASK.md   → Sadece şu anki görev
MEMORY.md         → Kritik kararlar ve notlar
```

Bu sayede 7B bir model bile bağlamı kaybetmeden büyük projeler üretebilir.

---

## 🗺️ Yol Haritası

- [x] Faz 1 — Sistem tarayıcı, LLM istemcisi, bağlam yöneticisi
- [x] Faz 2 — İstem toplayıcı, planlama ajanı, prompt şablonları
- [x] Faz 3 — Syntax doğrulama, bağımlılık tespiti, coder & editor ajanı
- [x] Faz 4 — Streamlit Web UI (4 sayfa)
- [x] Faz 5 — Proje şablon sistemi (FastAPI, React, Next.js, CLI)
- [ ] Faz 6 — GitHub Actions, demo, dokümantasyon

---

## 📄 Lisans

MIT
