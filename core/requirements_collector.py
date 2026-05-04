"""
LocalForge — Requirements Collector
Kullanıcıdan proje bilgilerini toplar ve yapılandırılmış dict döner.
Streamlit UI ile entegre çalışır.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

# Bilinen stack'ler → şablon eşleştirme için
KNOWN_STACKS = {
    "fastapi": [
        "fastapi",
        "fast api",
        "python api",
        "rest api python",
        "python backend",
    ],
    "react": ["react", "reactjs", "react.js", "vite react", "react typescript"],
    "nextjs": ["nextjs", "next.js", "next js", "next", "full stack react"],
    "cli": ["cli", "command line", "terminal tool", "komut satırı", "script"],
}

PLATFORM_OPTIONS = [
    "Web (Backend API)",
    "Web (Full Stack)",
    "Masaüstü",
    "CLI / Terminal",
    "Mobil",
]
DATABASE_OPTIONS = [
    "Yok",
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "MongoDB",
    "Redis",
    "Supabase",
]
AUTH_OPTIONS = ["Yok", "JWT", "Session", "OAuth2", "API Key"]


@dataclass
class ProjectRequirements:
    # Temel bilgiler
    name: str = ""
    description: str = ""
    goal: str = ""

    # Teknik tercihler
    stack: str = ""
    platform: str = ""
    database: str = "Yok"
    auth: str = "Yok"

    # Özellikler
    features: list[str] = field(default_factory=list)

    # Ek
    notes: str = "Yok"

    # Tespit edilen şablon (opsiyonel)
    detected_template: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_complete(self) -> bool:
        """Zorunlu alanların dolu olup olmadığını kontrol eder."""
        return bool(self.name and self.description and self.stack and self.platform)

    def to_summary(self) -> str:
        """LLM'e gönderilecek özet metin üretir."""
        features_text = (
            "\n".join(f"- {f}" for f in self.features)
            if self.features
            else "- Belirtilmedi"
        )
        return f"""
Proje Adı: {self.name}
Açıklama: {self.description}
Hedef: {self.goal}
Stack: {self.stack}
Platform: {self.platform}
Veritabanı: {self.database}
Kimlik Doğrulama: {self.auth}
Özellikler:
{features_text}
Ek Notlar: {self.notes}
""".strip()


def detect_template(stack: str) -> str:
    """
    Stack string'inden şablon adını tespit eder.
    Eşleşme yoksa boş string döner.
    """
    stack_lower = stack.lower()
    for template_name, keywords in KNOWN_STACKS.items():
        if any(kw in stack_lower for kw in keywords):
            return template_name
    return ""


def get_template_description(template_name: str) -> str:
    """Şablon adından kullanıcıya gösterilecek açıklamayı döner."""
    descriptions = {
        "fastapi": "FastAPI + SQLAlchemy + Pydantic iskeleti",
        "react": "React + Vite + TypeScript iskeleti",
        "nextjs": "Next.js 14 + App Router iskeleti",
        "cli": "Python CLI + Click + Rich iskeleti",
    }
    return descriptions.get(template_name, "")


# ─────────────────────────────────────────
# Streamlit UI için state yönetimi
# ─────────────────────────────────────────


def init_session_state(st) -> None:
    """
    Streamlit session_state'i başlatır.
    app.py veya ilgili sayfa başında çağrılır.
    """
    if "requirements" not in st.session_state:
        st.session_state.requirements = ProjectRequirements()
    if "template_accepted" not in st.session_state:
        st.session_state.template_accepted = None  # None | True | False
    if "collection_step" not in st.session_state:
        st.session_state.collection_step = 1


def render_collection_form(st) -> Optional[ProjectRequirements]:
    """
    Streamlit formunu render eder.
    Tamamlandığında ProjectRequirements döner, henüz tamamlanmadıysa None.
    """
    if not st.session_state.get("requirements"):
        st.session_state.requirements = ProjectRequirements()
    req: ProjectRequirements = st.session_state.requirements

    st.markdown("## 📋 Proje Bilgileri")
    st.caption("Alanları doldur, ajan projeyi sıfırdan planlayacak.")

    # ── Temel Bilgiler ──
    with st.expander("📌 Temel Bilgiler", expanded=True):
        req.name = st.text_input(
            "Proje adı", value=req.name, placeholder="örn: TaskManager API"
        )
        req.description = st.text_area(
            "Proje açıklaması (1-3 cümle)",
            value=req.description,
            placeholder="örn: Kullanıcıların görev oluşturup yönetebileceği REST API.",
            height=80,
        )
        req.goal = st.text_input(
            "Projenin ana hedefi",
            value=req.goal,
            placeholder="örn: Mobil uygulama için backend sağlamak",
        )

    # ── Teknik Tercihler ──
    with st.expander("⚙️ Teknik Tercihler", expanded=True):
        req.stack = st.text_input(
            "Teknoloji stack'i",
            value=req.stack,
            placeholder="örn: Python + FastAPI + PostgreSQL",
        )

        # Şablon tespiti
        if req.stack:
            detected = detect_template(req.stack)
            if detected and st.session_state.template_accepted is None:
                desc = get_template_description(detected)
                st.info(
                    f"💡 **{desc}** tespit edildi. Bu şablonu kullanmak ister misin?"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Evet, şablonu kullan", use_container_width=True):
                        req.detected_template = detected
                        st.session_state.template_accepted = True
                        st.rerun()
                with col2:
                    if st.button("❌ Hayır, sıfırdan planla", use_container_width=True):
                        req.detected_template = ""
                        st.session_state.template_accepted = False
                        st.rerun()
            elif st.session_state.template_accepted is True and req.detected_template:
                desc = get_template_description(req.detected_template)
                st.success(f"✅ Şablon seçildi: **{desc}**")
                if st.button("Şablonu kaldır"):
                    req.detected_template = ""
                    st.session_state.template_accepted = False
                    st.rerun()

        req.platform = st.selectbox(
            "Hedef platform",
            options=[""] + PLATFORM_OPTIONS,
            index=(
                PLATFORM_OPTIONS.index(req.platform) + 1
                if req.platform in PLATFORM_OPTIONS
                else 0
            ),
        )

        col1, col2 = st.columns(2)
        with col1:
            req.database = st.selectbox(
                "Veritabanı",
                options=DATABASE_OPTIONS,
                index=(
                    DATABASE_OPTIONS.index(req.database)
                    if req.database in DATABASE_OPTIONS
                    else 0
                ),
            )
        with col2:
            req.auth = st.selectbox(
                "Kimlik doğrulama",
                options=AUTH_OPTIONS,
                index=AUTH_OPTIONS.index(req.auth) if req.auth in AUTH_OPTIONS else 0,
            )

    # ── Özellikler ──
    with st.expander("✨ Özellikler", expanded=True):
        st.caption("Her satıra bir özellik yaz.")
        features_text = st.text_area(
            "Özellikler",
            value="\n".join(req.features),
            placeholder="Kullanıcı kayıt/giriş\nGörev oluşturma\nGörev kategorileri",
            height=120,
            label_visibility="collapsed",
        )
        req.features = [f.strip() for f in features_text.splitlines() if f.strip()]

    # ── Ek Notlar ──
    with st.expander("📝 Ek Notlar"):
        req.notes = st.text_area(
            "Kısıtlamalar veya özel istekler",
            value=req.notes if req.notes != "Yok" else "",
            placeholder="örn: Sadece async endpoint'ler kullanılsın, Docker desteği eklensin...",
            height=80,
        )
        if not req.notes:
            req.notes = "Yok"

    # ── REQUIREMENTS.md Önizleme ──
    with st.expander("👁️ REQUIREMENTS.md Önizleme"):
        preview = _generate_requirements_md(req)
        edited = st.text_area(
            "Direkt düzenleyebilirsin",
            value=preview,
            height=300,
            label_visibility="collapsed",
        )
        # Kullanıcı düzenlediyse kaydet
        if edited != preview:
            st.session_state["requirements_md_override"] = edited
            st.info("✏️ Manuel düzenleme kaydedildi.")

    # ── Gönder ──
    st.divider()

    if not req.is_complete():
        missing = []
        if not req.name:
            missing.append("Proje adı")
        if not req.description:
            missing.append("Açıklama")
        if not req.stack:
            missing.append("Stack")
        if not req.platform:
            missing.append("Platform")
        st.warning(f"Eksik alanlar: {', '.join(missing)}")
        return None

    if st.button("🚀 Planlamayı Başlat", type="primary", use_container_width=True):
        st.session_state.requirements = req
        return req

    return None


def _generate_requirements_md(req: ProjectRequirements) -> str:
    """ProjectRequirements'tan REQUIREMENTS.md içeriği üretir."""
    features_md = (
        "\n".join(f"- [ ] {f}" for f in req.features)
        if req.features
        else "- [ ] Belirtilmedi"
    )
    template_line = (
        f"\n## Şablon\n{get_template_description(req.detected_template)}"
        if req.detected_template
        else ""
    )

    return f"""# Gereksinimler — {req.name}

## Proje Açıklaması
{req.description}

## Hedef
{req.goal}

## Teknoloji Stack
{req.stack}

## Platform
{req.platform}

## Özellikler
{features_md}

## Veritabanı
{req.database}

## Kimlik Doğrulama
{req.auth}

## Ek Notlar
{req.notes}{template_line}
""".strip()
