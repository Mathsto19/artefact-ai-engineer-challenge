"""App-owned light/dark palettes, independent of native sidebar state."""


THEMES = {'Sistema': 'system', 'Claro': 'light', 'Escuro': 'dark'}
LIGHT = """
    --z-bg: #f4f7f6; --z-surface: #ffffff; --z-surface-alt: #eaf1ed;
    --z-text: #18332f; --z-muted: #526b64; --z-border: #b8cdc3;
    --z-accent: #116b5b; --z-on-accent: #ffffff; --z-selection: #c9e4d9;
    --z-user-bubble: #dff0e7;
    color-scheme: light;
"""
DARK = """
    --z-bg: #111a18; --z-surface: #1b2925; --z-surface-alt: #263831;
    --z-text: #e7f0eb; --z-muted: #c1d0c8; --z-border: #486257;
    --z-accent: #79d8b2; --z-on-accent: #10271e; --z-selection: #345c49;
    --z-user-bubble: #214a3b;
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
        [data-testid="stMainBlockContainer"] {
            max-width: 1480px !important; padding: 1rem 2rem 3rem !important;
            width: 100%; margin-inline: auto; box-sizing: border-box;
        }
        .st-key-app_controls { position: sticky; top: 0; z-index: 100;
            background: var(--z-bg); padding: .25rem 0 .5rem; }
        .st-key-conversation_navigation { background: var(--z-surface); padding: 1.35rem;
            border: 1px solid var(--z-border); border-radius: 14px;
            position: sticky; top: 1rem; max-height: calc(100dvh - 8rem);
            overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--z-border) transparent;
            display: block !important;
        }
        /* Normal document flow prevents a height-limited flex column from
           shrinking Markdown labels underneath the following controls. */
        .st-key-conversation_navigation > * {
            flex-shrink: 0 !important; margin-bottom: .75rem;
        }
        .st-key-conversation_navigation > :last-child { margin-bottom: 0; }
        .st-key-conversation_navigation [data-testid="stVerticalBlock"] {
            gap: .5rem; flex-shrink: 0 !important;
        }
        .st-key-conversation_navigation [data-testid="stElementContainer"] { flex-shrink: 0 !important; }
        .st-key-conversation_navigation .stButton button {
            text-align: left !important; justify-content: flex-start !important; min-height: 2.75rem;
            padding: .65rem .8rem; background: transparent; border-color: transparent;
        }
        .st-key-conversation_navigation .stButton button [data-testid="stMarkdownContainer"] {
            text-align: left !important; font-size: .95rem; width: 100%;
        }
        .st-key-conversation_navigation .stButton button > div { justify-content: flex-start !important; width: 100%; }
        .st-key-conversation_navigation .stButton button p {
            text-align: left !important; margin: 0; font-size: .95rem; line-height: 1.5;
        }
        .st-key-conversation_navigation .stButton button[kind="primary"] {
            background: var(--z-selection); border-color: var(--z-border); color: var(--z-text);
            box-shadow: inset 3px 0 0 var(--z-accent);
        }
        .st-key-conversation_navigation .stButton button[kind="primary"] [data-testid="stMarkdownContainer"] {
            color: var(--z-text);
        }
        .st-key-conversation_navigation .stButton button:hover { background: var(--z-surface-alt); }
        .st-key-conversation_navigation .stButton button[kind="secondary"] {
            background: transparent !important; color: var(--z-text) !important;
        }
        .st-key-conversation_navigation .stButton button[kind="secondary"]:hover {
            background: var(--z-surface-alt) !important;
        }
        .st-key-navigation_controls { padding: .25rem 0; }
        .st-key-navigation_controls .stButton button { border-color: var(--z-border); }
        .st-key-conversation_navigation .st-key-new_chat button[kind="primary"] {
            background: var(--z-accent); color: var(--z-on-accent); margin: .2rem 0 .5rem;
            box-shadow: none;
        }
        .st-key-conversation_navigation .st-key-new_chat button[kind="primary"] [data-testid="stMarkdownContainer"] {
            color: var(--z-on-accent);
        }
        .zubu-brand { display: flex; flex-direction: column; gap: .3rem; padding: .2rem 0 .4rem; }
        .zubu-brand-subtitle { font-size: .85rem; color: var(--z-muted); }
        .st-key-conversation_navigation .zubu-nav-heading {
            font-size: .9rem; line-height: 1.5; font-weight: 650;
            margin: 0; padding: 0 0 .55rem;
        }
        .st-key-conversation_navigation .zubu-nav-label {
            color: var(--z-muted); font-size: .86rem; line-height: 1.5;
            margin: 0; padding: 0 0 .6rem;
        }
        .st-key-navigation_examples, .st-key-navigation_personal,
        .st-key-navigation_tests, .st-key-navigation_footer {
            display: block !important; padding: 1.1rem 0; margin: 0 !important;
            border-top: 1px solid var(--z-border);
        }
        .st-key-navigation_examples > *, .st-key-navigation_personal > *,
        .st-key-navigation_tests > *, .st-key-navigation_footer > * {
            margin-bottom: .3rem; flex-shrink: 0 !important;
        }
        .st-key-navigation_footer { padding-bottom: 0; }
        .st-key-navigation_examples .stButton button {
            border: 1px solid var(--z-border); border-radius: 10px;
            padding: .65rem .75rem; min-height: 3rem;
        }
        .st-key-navigation_examples .zubu-nav-label {
            padding-bottom: 1rem;
        }
        .st-key-navigation_examples .stButton button[kind="secondary"] {
            background: var(--z-surface) !important;
        }
        .st-key-navigation_examples .stButton button:hover {
            border-color: var(--z-accent);
        }
        .st-key-navigation_examples .stButton button > div {
            flex: 1; min-width: 0; width: auto;
        }
        .st-key-navigation_examples .stButton button::after {
            content: '›'; flex-shrink: 0; margin-left: .6rem;
            color: var(--z-muted); font-size: 1.25rem; line-height: 1;
        }
        .st-key-navigation_examples > [data-testid="stElementContainer"]:has(.stButton) {
            margin-bottom: .5rem;
        }
        .st-key-navigation_footer .st-key-toggle_navigation button[kind="secondary"] {
            background: var(--z-surface) !important; border: 1px solid var(--z-border);
            border-radius: 8px; min-height: 2.65rem;
        }
        .st-key-navigation_footer .st-key-toggle_navigation button[kind="secondary"]:hover {
            background: var(--z-surface-alt) !important; border-color: var(--z-accent);
        }
        .st-key-navigation_footer > [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]) {
            padding-top: .6rem;
        }
        [data-testid="stPopoverButton"] {
            background: var(--z-surface) !important; color: var(--z-text) !important;
            border: 1px solid var(--z-border);
            border-radius: 8px; min-height: 2.65rem;
        }
        [data-testid="stPopoverBody"] { background: var(--z-surface); color: var(--z-text); border-color: var(--z-border); }
        [data-testid="stTooltipContent"], [role="tooltip"] {
            background: var(--z-surface-alt) !important; color: var(--z-text) !important;
            border: 1px solid var(--z-border); border-radius: 8px;
        }
        [data-testid="stTooltipContent"] [data-testid="stMarkdownContainer"],
        [data-testid="stTooltipContent"] p { color: var(--z-text) !important; }
        [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
        [data-testid="stText"], .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: var(--z-text);
        }
        [data-testid="stCaptionContainer"] { color: var(--z-muted); }
        [data-testid="stCaptionContainer"] [data-testid="stMarkdownContainer"] { color: var(--z-muted); }
        .stButton button, .stDownloadButton button {
            border-radius: 8px; min-height: 2.65rem; background: var(--z-surface);
            border-color: var(--z-border); color: var(--z-text);
        }
        .stButton button[kind="primary"] { background: var(--z-accent);
            border-color: var(--z-accent); color: var(--z-on-accent); }
        .stButton button[kind="primary"] [data-testid="stMarkdownContainer"] { color: var(--z-on-accent); }
        .stButton button:hover, .stDownloadButton button:hover { border-color: var(--z-accent); }
        .stButton button:focus-visible, .stDownloadButton button:focus-visible {
            outline: 2px solid var(--z-accent); outline-offset: 2px;
        }
        .zubu-banner { border-bottom: 1px solid var(--z-border); padding-bottom: 1.25rem; margin-bottom: 1.5rem; }
        .zubu-banner h2 { margin: 0; font-size: 1.35rem; color: var(--z-text); }
        .zubu-banner p { margin: .4rem 0 0; font-size: .95rem; color: var(--z-muted); }
        .st-key-conversation_header {
            background: transparent; border: 0; border-bottom: 1px solid var(--z-border);
            border-radius: 0; padding: .5rem 0 1.1rem; margin-bottom: 1.25rem;
            display: block !important;
        }
        .st-key-conversation_header > * { flex-shrink: 0 !important; }
        .zubu-chat-heading { min-width: 0; padding: .15rem 0; }
        .st-key-conversation_header .zubu-chat-heading h2 {
            font-size: 1.2rem; line-height: 1.4; margin: 0;
            padding: 0; font-weight: 650; overflow-wrap: anywhere;
        }
        .zubu-chat-heading .zubu-heading-subtitle {
            font-size: .85rem; line-height: 1.5; color: var(--z-muted); margin: 0; padding-top: .25rem;
        }
        .st-key-conversation_header [data-testid="stPopoverButton"] {
            background: transparent !important; border-color: transparent; min-height: 2.4rem;
        }
        .st-key-conversation_header [data-testid="stPopoverButton"]:hover {
            background: var(--z-surface-alt) !important; border-color: var(--z-border);
        }
        .st-key-delete_chat button {
            background: transparent; border-color: transparent; min-height: 2.25rem; padding: .35rem .5rem;
        }
        .st-key-delete_chat button:hover { background: var(--z-surface-alt); border-color: var(--z-border); }
        .zubu-sidebar-title { color: var(--z-accent); font-weight: 750; font-size: 1.5rem; }
        [data-testid="stChatMessage"] { background: var(--z-surface); color: var(--z-text);
            border: 1px solid var(--z-border); border-radius: 4px 16px 16px 16px;
            padding: 1rem 1.15rem; margin: 0 auto .65rem 0;
            width: fit-content !important; max-width: 88%; min-width: 0;
        }
        [data-testid="stChatMessage"]:has([aria-label="Chat message from Você"]),
        [data-testid="stChatMessage"]:has([aria-label="Chat message from Cliente"]) {
            margin-left: auto; margin-right: 0; max-width: 80%;
            background: var(--z-user-bubble); border-radius: 16px 4px 16px 16px;
            flex-direction: row-reverse;
        }
        [data-testid="stChatMessageContent"] { min-width: 0; overflow-wrap: anywhere; }
        [data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }
        [data-testid="stChatMessage"] [data-testid="stExpander"] {
            margin-top: .35rem;
        }
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
        [data-testid="stBottom"] > div { background: var(--z-bg); }
        [data-testid="stBottomBlockContainer"] {
            max-width: 1480px !important; width: 100%; margin-inline: auto;
            padding: .75rem 2rem 1rem !important; box-sizing: border-box;
        }
        /* Native columns subtract the full gap from each flex basis, then
           share the remaining free gap equally: 75% minus half the gap. */
        @media (min-width: 721px) {
            .stApp:has(.st-key-conversation_navigation)
            [data-testid="stBottomBlockContainer"] [data-testid="stChatInput"] {
                width: calc(75% - 1rem) !important; margin-left: auto; margin-right: 0;
            }
        }
        ::selection { background: var(--z-selection); color: var(--z-text); }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] { padding: .5rem .75rem 2rem !important; }
            [data-testid="stBottomBlockContainer"] { padding: .5rem .75rem .75rem !important; }
            .st-key-conversation_navigation { position: static; max-height: 50dvh; }
            .zubu-banner h2 { font-size: 1.15rem; }
            [data-testid="stChatMessage"] { max-width: 94%; padding: .65rem .75rem; }
            [data-testid="stChatMessage"]:has([aria-label="Chat message from Você"]),
            [data-testid="stChatMessage"]:has([aria-label="Chat message from Cliente"]) { max-width: 90%; }
        }
    </style>"""
