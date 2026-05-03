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
├── app.py                  # Streamlit giriş noktası
├── setup.py                # Otomatik kurulum
├── requirements.txt
│
├── core/
│   ├── system_scanner.py       # Donanım tespiti
│   ├── llm_recommender.py      # Model önerileri
│   ├── llm_client.py           # Ollama / LM Studio istemcisi
│   ├── context_manager.py      # MD tabanlı bağlam yönetimi
│   ├── syntax_validator.py     # Kod doğrulama
│   ├── dependency_scanner.py   # Import tarayıcı
│   ├── checkpoint_manager.py   # Snapshot sistemi
│   └── file_writer.py          # Kod yazıcı
│
├── agents/
│   ├── planner_agent.py        # Mimari + görev listesi üretir
│   ├── coder_agent.py          # Dosya dosya kod yazar
│   └── editor_agent.py         # Düzenleme & refactor
│
├── prompts/                    # LLM sistem promptları
├── templates/                  # Opsiyonel proje iskeletleri
└── ui/                         # Streamlit sayfa bileşenleri
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
- [ ] Faz 2 — İstem toplayıcı, planlama ajanı, prompt şablonları
- [ ] Faz 3 — Syntax doğrulama, bağımlılık tespiti, checkpoint sistemi
- [ ] Faz 4 — Streamlit Web UI
- [ ] Faz 5 — Proje şablon sistemi
- [ ] Faz 6 — GitHub Actions, demo, dokümantasyon

---

## 📄 Lisans

MIT