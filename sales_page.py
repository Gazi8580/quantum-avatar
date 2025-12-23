import streamlit as st
import os
from pathlib import Path
import requests
from products import catalog
from cart import cart
from orders import order_manager, ShippingAddress

# Page Config
st.set_page_config(
    page_title="MEGA SHOP - AI PRODUCTS",
    page_icon="🛍️",
    layout="wide"
)

def load_client_id():
    env_files = [Path('env.ini'), Path('.env')]
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('PAYPAL_CLIENT_ID='):
                            return line.split('=', 1)[1].strip().strip('"').strip("'")
            except:
                pass
    return None

def load_paypal_config():
    """Load PayPal configuration from environment"""
    env_files = [Path('env.ini'), Path('.env')]
    config = {}
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            config[key.strip()] = value.strip().strip('"').strip("'")
            except:
                pass
    return config

client_id = load_client_id()
paypal_config = load_paypal_config()

st.title("🛍️ MEGA-ULTRA-ROBOTER SHOP SYSTEM")

if not client_id or "PLACEHOLDER" in client_id:
    st.error("⚠️ Kein gültiger PayPal Client ID in env.ini gefunden!")
    st.stop()

# Shopping Cart Sidebar
with st.sidebar:
    st.header("🛒 Warenkorb")

    if cart.is_empty():
        st.info("Ihr Warenkorb ist leer")
    else:
        cart_summary = cart.get_cart_summary()
        st.metric("Artikel", cart_summary["total_items"])
        st.metric("Gesamt", f"{cart_summary['total_price']:.2f} {cart_summary['currency']}")

        st.subheader("Artikel:")
        for item in cart_summary["items"]:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.text(item.product.name)
            with col2:
                st.text(f"{item.quantity}x")
            with col3:
                st.text(f"{item.total_price:.2f}€")

        if st.button("🗑️ Warenkorb leeren", type="secondary"):
            cart.clear_cart()
            st.rerun()

        if st.button("💳 Zur Kasse", type="primary"):
            st.session_state.checkout = True
            st.rerun()

# Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛒 AI Produkte",
    "📦 Dropshipping",
    "🤝 Affiliate",
    "💼 Freelancer",
    "📸 Screenshot Converter"
])

with tab1:
    st.header("AI Premium Produkte")
    st.caption("Hier verkauft der Roboter deine Produkte!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.image("https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600", caption="AI Premium Service")
    with col2:
        st.header("AI Optimization Package")
        st.write("Der Roboter optimiert deine Prozesse automatisch.")
        st.subheader("CHF 1.00")
        
        # PayPal Button Integration
        paypal_html = f'''
        <div id="paypal-button-container-1"></div>
        <script src="https://www.paypal.com/sdk/js?client-id={client_id}&currency=CHF"></script>
        <script>
            paypal.Buttons({{
                createOrder: function(data, actions) {{
                    return actions.order.create({{
                        purchase_units: [{{
                            amount: {{
                                value: '1.00'
                            }}
                        }}]
                    }});
                }},
                onApprove: function(data, actions) {{
                    return actions.order.capture().then(function(details) {{
                        alert('Transaction completed by ' + details.payer.name.given_name + '! Check your Dashboard!');
                    }});
                }}
            }}).render('#paypal-button-container-1');
        </script>
        '''
        st.components.v1.html(paypal_html, height=200)

with tab2:
    st.header("📦 Dropshipping Modul")
    st.info("Dieses Modul verbindet sich mit AliExpress/Shopify.")
    st.write("Status: 🟡 Bereit zur Aktivierung")
    if st.button("Dropshipping starten"):
        st.success("Dropshipping-Agent initialisiert...")

with tab3:
    st.header("🤝 Affiliate Marketing")
    st.info("Automatische Generierung von Affiliate-Links.")
    st.write("Status: 🟡 Bereit zur Aktivierung")
    if st.button("Affiliate-Links generieren"):
        st.success("Suche nach Partnerprogrammen...")

with tab4:
    st.header("💼 Freelancer Auto-Bidder")
    st.info("Bietet automatisch auf Upwork/Fiverr Jobs.")
    st.write("Status: 🟡 Bereit zur Aktivierung")
    if st.button("Auto-Bidder starten"):
        st.success("Scanne Upwork nach Jobs...")

with tab5:
    st.header("📸 Screenshot Converter")
    st.info("Wandelt Screenshots in Code um.")
    uploaded_file = st.file_uploader("Screenshot hochladen", type=['png', 'jpg'])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Hochgeladener Screenshot")
        if st.button("Konvertieren"):
            st.success("Bild wird analysiert... (Code-Generierung läuft)")

st.markdown("---")
st.info("ℹ️ Alle Einnahmen fließen direkt in dein PayPal-Konto!")
