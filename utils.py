
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import openpyxl
import warnings

warnings.filterwarnings('ignore')

def process_transposed_data(df, date_columns, id_columns):
    """
    Convierte datos transpuestos (fechas como columnas) a formato largo
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # Verificar que las columnas de fecha existen
    available_date_cols = [col for col in date_columns if col in df.columns]
    if not available_date_cols:
        return pd.DataFrame()

    # Hacer melt para convertir de formato ancho a largo
    df_melted = pd.melt(
        df,
        id_vars=id_columns,
        value_vars=available_date_cols,
        var_name='Fecha',
        value_name='Valor'
    )

    # Convertir fecha a datetime
    df_melted['Fecha'] = pd.to_datetime(df_melted['Fecha'], format='%b-%y', errors='coerce')

    # Filtrar valores no nulos
    df_melted = df_melted.dropna(subset=['Valor'])
    df_melted = df_melted[df_melted['Valor'] != 0]

    return df_melted


def process_investments_data(df):
    """
    Procesa datos de inversiones con estructura compleja (multiheader)
    Cada fecha tiene subcolumnas: Títulos, Precio medio, Precio actual
    """

def load_and_process_data(uploaded_file):
    """
    Carga y procesa el archivo Excel con todas las hojas
    """
    try:
        # Leer todas las hojas del Excel
        excel_data = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')

        data = {}

        # Procesar Transacciones
        if 'Transacciones' in excel_data:
            trans_df = excel_data['Transacciones']
            if not trans_df.empty:
                trans_df['Fecha'] = pd.to_datetime(trans_df['Fecha'], errors='coerce')
                trans_df['Mes_Año'] = trans_df['Fecha'].dt.strftime('%b-%Y')
                trans_df['Importe'] = pd.to_numeric(trans_df['Importe'], errors='coerce')
                data['transacciones'] = trans_df.dropna(subset=['Fecha', 'Importe'])

        # Procesar Presupuesto
        if 'Presupuesto' in excel_data:
            pres_df = excel_data['Presupuesto']
            if not pres_df.empty:
                id_cols = ['Cuenta', 'Categoria', 'Tipo']
                available_id_cols = [col for col in id_cols if col in pres_df.columns]
                date_cols = [col for col in pres_df.columns if col not in id_cols]
                data['presupuesto'] = process_transposed_data(pres_df, date_cols, available_id_cols)
                data['presupuesto']['Mes_Año'] = data['presupuesto']['Fecha'].dt.strftime('%b-%Y')

        # Procesar Saldos
        if 'Saldos' in excel_data:
            saldos_df = excel_data['Saldos']
            if not saldos_df.empty:
                id_cols = ['Nombre', 'Tipo de Cuenta']
                available_id_cols = [col for col in id_cols if col in saldos_df.columns]
                date_cols = [col for col in saldos_df.columns if col not in id_cols]
                data['saldos'] = process_transposed_data(saldos_df, date_cols, available_id_cols)

        # Procesar Deudas
        if 'Deudas' in excel_data:
            deudas_df = excel_data['Deudas']
            if not deudas_df.empty:
                id_cols = ['Nombre', 'Tipo de Deuda']
                available_id_cols = [col for col in id_cols if col in deudas_df.columns]
                date_cols = [col for col in deudas_df.columns if col not in id_cols]
                data['deudas'] = process_transposed_data(deudas_df, date_cols, available_id_cols)

        # Procesar Inversiones
        if 'Inversiones' in excel_data:
            inv_df = excel_data['Inversiones']
            inv_df = inv_df.fillna(method = 'ffill')
            data['inversiones'] = process_investments_data(inv_df)
            if not inv_df.empty:
                id_cols = ['Tipo de Activo', 'Nombre', 'Categoría', 'Métrica']
                date_cols = [col for col in inv_df.columns if col not in id_cols]
                available_id_cols = [col for col in id_cols if col in inv_df.columns]
                data['inversiones'] = process_transposed_data(inv_df, date_cols, available_id_cols)
                data['inversiones'] = data['inversiones'].pivot_table(
                    index=["Tipo de Activo", "Nombre", "Categoría", "Fecha"],
                    columns="Métrica",
                    values="Valor",
                    aggfunc="sum",
                    fill_value=0
                ).reset_index()
                data['inversiones']['Valor Actual'] = data['inversiones']['Títulos']*data['inversiones']['Precio actual']
                data['inversiones']['Valor Compra'] = data['inversiones']['Títulos']*data['inversiones']['Precio medio']
        return data

    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        return None