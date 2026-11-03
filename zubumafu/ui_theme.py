"""App-owned light/dark palettes, independent of native sidebar state."""


THEMES = {'Sistema': 'system', 'Claro': 'light', 'Escuro': 'dark'}
LIGHT = """
    --z-bg: #f4f7f6; --z-surface: #ffffff; --z-surface-alt: #eaf1ed;
    --z-text: #18332f; --z-muted: #526b64; --z-border: #b8cdc3;
    --z-accent: #116b5b; --z-on-accent: #ffffff; --z-selection: #c9e4d9;
    color-scheme: light;
"""
DARK = """
    --z-bg: #111a18; --z-surface: #1b2925; --z-surface-alt: #263831;
    --z-text: #e7f0eb; --z-muted: #b0c4ba; --z-border: #486257;
    --z-accent: #79d8b2; --z-on-accent: #10271e; --z-selection: #345c49;
    color-scheme: dark;
"""


def theme_css(mode: str) -> str:
    if mode == 'Escuro':
        variables = ':root {' + DARK + '}'
    elif mode == 'Claro':
        variables = ':root {' + LIGHT + '}'
    else:
        variables = ':root {' + LIGHT + '} @media (prefers-color-scheme: dark) { :root {' + DARK + '} }'
    return '<style>' + variables + """
        html, body, .stApp, [data-testid="stMain"] {
            background: var(--z-bg); color: var(--z-text);
        }
        /* Navigation uses real app buttons; the unused native header/sidebar
           are not involved in opening or closing the conversation panel. */
        [data-testid="stHeader"] { display: none; }
        [data-testid="stMainBlockContainer"] { max-width: 1480px; padding: 1rem 2rem 3rem; }
        .st-key-app_controls { position: sticky; top: 0; z-index: 100;
            background: var(--z-bg); padding: .5rem 0 .75rem; }
        .st-key-conversation_navigation { background: var(--z-surface); padding: 1rem;
            border: 1px solid var(--z-border); border-radius: 12px;
            position: sticky; top: 6rem; max-height: calc(100dvh - 7rem); overflow-y: auto; }
        .st-key-conversation_navigation .stButton > button { text-align: left; justify-content: flex-start; }
        [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
        [data-testid="stText"], .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: var(--z-text);
        }
        [data-testid="stCaptionContainer"] { color: var(--z-muted); }
        [data-testid="stCaptionContainer"] [data-testid="stMarkdownContainer"] { color: var(--z-muted); }
        .stButton > button, .stDownloadButton > button {
            border-radius: 8px; min-height: 2.65rem; background: var(--z-surface);
            border-color: var(--z-border); color: var(--z-text);
        }
        .stButton > button[kind="primary"] { background: var(--z-accent);
            border-color: var(--z-accent); color: var(--z-on-accent); }
        .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] { color: var(--z-on-accent); }
        .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--z-accent); }
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
            outline: 2px solid var(--z-accent); outline-offset: 2px;
        }
        .zubu-banner { border-bottom: 1px solid var(--z-border); padding-bottom: 1.25rem; margin-bottom: 1.5rem; }
        .zubu-banner h2 { margin: 0; font-size: 1.35rem; color: var(--z-text); }
        .zubu-banner p { margin: .4rem 0 0; font-size: .95rem; color: var(--z-muted); }
        .zubu-sidebar-title { color: var(--z-accent); font-weight: 750; font-size: 1.5rem; }
        [data-testid="stChatMessage"] { background: var(--z-surface); color: var(--z-text);
            border: 1px solid var(--z-border); border-radius: 12px; padding: 1rem; margin-bottom: .75rem; }
        [data-testid^="stChatMessageAvatar"] {
            background: var(--z-surface-alt); color: var(--z-text);
            border: 1px solid var(--z-border);
        }
        [data-testid^="stChatMessageAvatar"] [data-testid="stIconMaterial"],
        [data-testid="stChatMessage"] > [data-testid="stIconMaterial"] {
            color: var(--z-text) !important;
        }
        [data-testid^="stChatMessageAvatar"] svg { color: var(--z-text); }
        [data-testid="stChatInput"], [data-baseweb="base-input"] {
            background: var(--z-surface); border-color: var(--z-border); border-radius: 10px;
        }
        /* The native chat input paints its inner wrapper separately. */
        [data-testid="stChatInput"] > div {
            background: var(--z-surface) !important;
            color: var(--z-text); border-color: var(--z-border) !important;
        }
        [data-testid="stChatInput"] > div:focus-within {
            border-color: var(--z-accent) !important;
        }
        [data-testid="stChatInput"] textarea {
            background: transparent !important;
        }
        [data-testid="stChatInput"] textarea, .stApp input, .stApp textarea {
            background: var(--z-surface); color: var(--z-text); caret-color: var(--z-accent);
        }
        [data-testid="stChatInputSubmitButton"] { background: var(--z-surface-alt); color: var(--z-text); }
        [data-testid="stChatInputSubmitButton"]:disabled { color: var(--z-muted); }
        .stApp textarea::placeholder, .stApp input::placeholder { color: var(--z-muted); opacity: 1; }
        [data-baseweb="select"] > div, [data-baseweb="popover"], [role="listbox"],
        [role="option"], [data-baseweb="menu"] {
            background: var(--z-surface); color: var(--z-text); border-color: var(--z-border);
        }
        [role="option"]:hover, [role="option"][aria-selected="true"] { background: var(--z-surface-alt); }
        [data-baseweb="select"] [role="combobox"], [data-baseweb="select"] span { color: var(--z-text); }
        [data-baseweb="select"] svg { fill: var(--z-text); }
        /* Streamlit 1.66 selectboxes use React Aria rather than Base Web. */
        [data-testid="stSelectbox"] > div,
        [data-testid="stSelectbox"] [role="group"] {
            background: var(--z-surface) !important;
            color: var(--z-text); border-color: var(--z-border) !important;
        }
        [data-testid="stSelectbox"] [role="group"]:focus-within {
            border-color: var(--z-accent) !important;
        }
        [data-testid="stSelectbox"] input,
        [data-testid="stSelectbox"] button {
            background: transparent !important; color: var(--z-text) !important;
        }
        [data-testid="stSelectbox"] button:hover {
            background: var(--z-surface-alt) !important;
        }
        [data-testid="stSelectbox"] svg { color: var(--z-text); }
        [data-testid="stSelectboxVirtualDropdown"] {
            background: var(--z-surface) !important;
            color: var(--z-text); border-color: var(--z-border) !important;
        }
        .stApp a { color: var(--z-accent); }
        [data-testid="stExpander"], [data-testid="stAlert"], [data-testid="stStatusWidget"] {
            background: var(--z-surface); color: var(--z-text); border-color: var(--z-border);
        }
        [data-testid="stExpander"] details, [data-testid="stExpander"] summary {
            background: var(--z-surface); color: var(--z-text); border-color: var(--z-border);
        }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--z-border); }
        [data-testid="stJson"], .stApp pre, .stApp code { background: var(--z-surface-alt); color: var(--z-text); }
        [data-testid="stJson"] * { background-color: transparent !important; color: var(--z-text) !important; }
        [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] { background: var(--z-bg); }
        [data-testid="stBottomBlockContainer"] {
            max-width: 1480px !important; width: 100%; margin-inline: auto;
            padding: .75rem 2rem 1rem !important; box-sizing: border-box;
        }
        /* Match the 1:3 conversation columns and their large (4rem) gap,
           while preserving Streamlit's native bottom anchoring. */
        @media (min-width: 721px) {
            .stApp:has(.st-key-conversation_navigation)
            [data-testid="stBottomBlockContainer"] [data-testid="stChatInput"] {
                width: calc(75% - 3rem); margin-left: auto;
            }
        }
        ::selection { background: var(--z-selection); color: var(--z-text); }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] { padding: .5rem .75rem 2rem; }
            [data-testid="stBottomBlockContainer"] { padding: .5rem .75rem .75rem !important; }
            .st-key-conversation_navigation { position: static; max-height: 50dvh; }
            .zubu-banner h2 { font-size: 1.15rem; }
        }
    </style>"""
