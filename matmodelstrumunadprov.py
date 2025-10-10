import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import sys
import subprocess

# --- АВТОМАТИЧНА УСТАНОВКА БИБЛИОТЕК ---
try:
    import streamlit as st
except ImportError:
    print("Бібліотека 'streamlit' не знайдена. Спроба встановити...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Моделювання струму", layout="wide")
st.title("🔬 МОДЕЛЮВАННЯ ДИНАМІКИ ГУСТИНИ СТРУМУ")
st.markdown("---")

# --- ФИЗИЧЕСКИЕ КОНСТАНТЫ ---
E_CHARGE = 1.6e-19
M_ELECTRON = 9.1e-31
N_0 = 1.0e29
T_C = 9.2
TAU = 2e-14

# --- САЙДБАР ДЛЯ ВВОДА ПАРАМЕТРОВ ---
with st.sidebar:
    st.header("🎛️ Параметри моделювання")
    
    # Выбор температуры
    T = st.slider("🌡️ Температура T (K)", 0.1, 20.0, 4.0, 0.1)
    
    # Определение состояния
    is_superconductor = (T < T_C)
    if is_superconductor:
        st.success(f"⚡ Надпровідний стан: T={T}K < T_c={T_C}K")
        N_S = N_0 * (1 - (T / T_C) ** 4)
        K_COEFF = (N_S * E_CHARGE**2) / M_ELECTRON
        st.metric("Лондонівський коефіцієнт K", f"{K_COEFF:.2e}")
    else:
        st.info(f"🔌 Звичайний метал: T={T}K ≥ T_c={T_C}K")
        SIGMA_COEFF = (N_0 * E_CHARGE**2 * TAU) / M_ELECTRON
        st.metric("Провідність Друде σ", f"{SIGMA_COEFF:.2e} См/м")
    
    # Начальный ток
    J_0 = st.number_input("➡️ Початкова густина струму j₀ (А/м²)", 
                         min_value=0.0, max_value=1e11, value=1e9, step=1e8)
    
    # Тип поля
    st.subheader("📊 Тип зовнішнього поля")
    field_type = st.selectbox("Оберіть тип поля:", 
                             ["Постійне поле: E(t) = E₀", 
                              "Лінійне поле: E(t) = a · t", 
                              "Синусоїдальне: E(t) = E₀ · sin(ωt)"])
    
    # Параметры поля
    if "Постійне" in field_type:
        E_0 = st.number_input("E₀ (В/м)", 0.0, 1e4, 1e3, 100.0)
        formula = r'$E(t) = E_0$'
    elif "Лінійне" in field_type:
        A = st.number_input("Швидкість зростання 'a' (В/(м·с))", 1e8, 1e12, 1e10, 1e9)
        formula = r'$E(t) = a \cdot t$'
    else:  # Синусоидальное
        E_0 = st.number_input("Амплітуда E₀ (В/м)", 0.0, 1e4, 1e3, 100.0)
        F = st.number_input("Частота f (Гц)", 1e6, 1e9, 1e7, 1e6)
        OMEGA = 2 * np.pi * F
        formula = r'$E(t) = E_0 \sin(\omega t)$'

# --- РАСЧЕТЫ ---
T_END = 1e-9
T_ARRAY = np.linspace(0, T_END, 1000)
J_ARRAY = np.zeros_like(T_ARRAY)
formula_label = ""

# Расчет тока
if is_superconductor:
    if "Постійне" in field_type:
        J_ARRAY = J_0 + K_COEFF * E_0 * T_ARRAY
        formula_label = r'$j(t) = j_0 + K E_0 t$'
    elif "Лінійне" in field_type:
        J_ARRAY = J_0 + (K_COEFF * A * T_ARRAY**2) / 2
        formula_label = r'$j(t) = j_0 + \frac{1}{2} K a t^2$'
    else:  # Синусоидальное
        J_ARRAY = J_0 + (K_COEFF * E_0 / OMEGA) * (1 - np.cos(OMEGA * T_ARRAY))
        formula_label = r'$j(t) = j_0 + \frac{K E_0}{\omega} (1 - \cos(\omega t))$'
else:
    sigma = (N_0 * E_CHARGE**2 * TAU) / M_ELECTRON
    if "Постійне" in field_type:
        J_ARRAY = J_0 * np.exp(-T_ARRAY / TAU) + sigma * E_0 * (1 - np.exp(-T_ARRAY / TAU))
        formula_label = r'$j(t) = j_0 e^{-t/\tau} + \sigma E_0 (1 - e^{-t/\tau})$'
    elif "Лінійне" in field_type:
        J_ARRAY = J_0 * np.exp(-T_ARRAY / TAU) + sigma * A * (T_ARRAY - TAU * (1 - np.exp(-T_ARRAY / TAU)))
        formula_label = r'$j(t) = j_0 e^{-t/\tau} + \sigma a [t - \tau(1 - e^{-t/\tau})]$'
    else:  # Синусоидальное
        phase_shift = np.arctan(OMEGA * TAU)
        amplitude_factor = sigma / np.sqrt(1 + (OMEGA * TAU)**2)
        J_ST = E_0 * amplitude_factor * np.sin(OMEGA * T_ARRAY - phase_shift)
        C = J_0 - E_0 * amplitude_factor * np.sin(-phase_shift)
        J_TR = C * np.exp(-T_ARRAY / TAU)
        J_ARRAY = J_TR + J_ST
        formula_label = r'$j(t) = j_{\text{tr}}(t) + j_{\text{st}}(t)$'

# --- ВИЗУАЛИЗАЦИЯ ---
st.subheader("📈 Результати моделювання")
st.latex(formula_label)

# Создание графика
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(T_ARRAY * 1e9, J_ARRAY, 'b-', linewidth=2.5)

ax.set_xlabel('Час $t$ (нс)', fontsize=12)
ax.set_ylabel('Густина струму $j$ (${\\text{A}}/{\\text{м}^2}$)', fontsize=12)
ax.set_title(f'Динаміка густини струму: T = {T} K', fontsize=14)
ax.grid(True, linestyle='--', alpha=0.7)
ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))

# Показать график в Streamlit
st.pyplot(fig)

# --- РЕЗУЛЬТАТЫ ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Максимальний струм", f"{np.max(J_ARRAY):.2e} А/м²")
with col2:
    st.metric("Мінімальний струм", f"{np.min(J_ARRAY):.2e} А/м²")
with col3:
    st.metric("Час моделювання", "1 нс")

# --- ЭКСПОРТ ДАННЫХ ---
st.subheader("💾 Експорт результатів")
if st.button("Зберегти графік як PNG"):
    fig.savefig("graph.png")
    st.success("Графік збережено як 'graph.png'")
    st.balloons()

# --- ИНФОРМАЦИЯ ---
with st.expander("ℹ️ Довідка"):
    st.markdown("""
    **Фізичні принципи:**
    - **Надпровідник**: Рівняння Лондонів - струм росте без опору
    - **Звичайний метал**: Модель Друде - струм виходить на стаціонарний рівень
    
    **Параметри за замовчуванням відповідають ніобію (Nb).**
    """)
