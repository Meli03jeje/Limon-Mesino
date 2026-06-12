# 🚛 CVRP · Florida Bebidas — Provincia de Cartago

> **II-1122 · Flujos de Redes** · Prof. David Benavides · UCR Sede Alajuela · I-2026

Aplicación de optimización de rutas de distribución (CVRP) para la provincia de **Cartago, Costa Rica**, usando la planta en Río Segundo, Alajuela como centro de distribución.

---

## 📋 Descripción del problema

### Modelo en tres fases

| Fase | Descripción |
|------|-------------|
| **1. Demanda** | Cada cantón demanda pallets/semana (split 50/25/25: Imperial, Pilsen, Tropical) |
| **2. Flota** | Camiones de 24 pallets. Flota mínima = ⌈demanda total ÷ 24⌉ |
| **3. Ruteo (CVRP)** | Cada camión sale del CD, visita cantones sin pasar de 24 pallets y regresa |

### Formulación matemática

**Función objetivo:**
```
min Σ_k Σ_i Σ_j d_ij · x_ijk
```

**Restricciones:**
1. **Flujo vehicular:** Camión entra = Camión sale en cada nodo
2. **Satisfacción de demanda:** Entradas − Salidas = Demanda del cantón
3. **Capacidad (Big-M):** Cada camión lleva máximo 24 pallets
4. **Eliminación de subtours:** Restricciones MTZ

**Método:** Heurística Clarke-Wright Savings (óptima para instancias pequeñas).

---

## 🗺️ Datos de Cartago

### Cantones (8 + CD depósito)

| Nodo | Cantón | Demanda (pallets/sem) |
|------|--------|-----------------------|
| 0 | CD Cartago (depósito) | — |
| 1 | Cartago | 124 |
| 2 | Paraíso | 48 |
| 3 | La Unión | 75 |
| 4 | Jiménez | 15 |
| 5 | Turrialba | 61 |
| 6 | Alvarado | 12 |
| 7 | Oreamuno | 36 |
| 8 | El Guarco | 35 |

**Total:** 406 pallets/semana · **Flota mínima:** 17 camiones de 24 pallets

---

## 🚀 Instalación y ejecución

### Prerequisitos
- Python 3.10+
- pip

### Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/cvrp-cartago.git
cd cvrp-cartago

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la app
streamlit run app.py
```

La app abre en `http://localhost:8501`

---

## ☁️ Deploy en Streamlit Community Cloud

1. Subir este repositorio a GitHub (público o privado)
2. Ir a [share.streamlit.io](https://share.streamlit.io)
3. Conectar con tu cuenta de GitHub
4. Seleccionar el repositorio y el archivo `app.py`
5. Click en **Deploy** ✅

> No se necesita configuración adicional. Streamlit Cloud instala automáticamente las dependencias de `requirements.txt`.

---

## 📁 Estructura del proyecto

```
cvrp-cartago/
├── app.py              # Aplicación principal Streamlit
├── requirements.txt    # Dependencias Python
├── README.md           # Este archivo
└── .streamlit/
    └── config.toml     # Configuración de tema (opcional)
```

---

## 🧮 Tecnologías

| Componente | Tecnología |
|-----------|-----------|
| Interfaz | Streamlit |
| Optimización | PuLP + Clarke-Wright Heuristic |
| Mapas | Folium + streamlit-folium |
| Datos | Pandas + NumPy |
| Deploy | Streamlit Community Cloud / GitHub |

---

## 📖 Referencias

- Clarke, G. & Wright, J.W. (1964). *Scheduling of vehicles from a central depot to a number of delivery points*. Operations Research, 12(4), 568–581.
- Toth, P. & Vigo, D. (2014). *Vehicle Routing: Problems, Methods, and Applications*. SIAM.
- Datos de demanda y distancias: Florida Bebidas, Cartago, Costa Rica (caso académico).

---

*Proyecto académico — II-1122 Flujos de Redes · UCR Sede Alajuela · I-2026*
