import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from streamlit_js_eval import streamlit_js_eval

import openpyxl
import warnings

from utils import load_and_process_data

def load_patrimonio_kpis(data):
    col1, col2, col3, col4, col5 = st.columns(5)
    if 'saldos' in data and not data['saldos'].empty:
        saldos_df = data['saldos']

        # Métricas principales

        saldo_actual = saldos_df.groupby('Fecha')['Valor'].sum().iloc[-1] if not saldos_df.empty else 0
        saldo_pm = saldos_df.groupby('Fecha')['Valor'].sum().iloc[-2] if not saldos_df.empty else 0
        growth_saldo = (saldo_actual - saldo_pm) * 100/saldo_pm

        deuda_actual = data['deudas'].groupby('Fecha')['Valor'].sum().iloc[-1] if not data['deudas'].empty else 0
        deuda_pm = data['deudas'].groupby('Fecha')['Valor'].sum().iloc[-2] if not data['deudas'].empty else 0
        growth_deuda = (deuda_actual - deuda_pm) * 100 / deuda_pm

        porc_deuda_actual = round(deuda_actual*100/saldo_actual, 2)
        porc_deuda_pm = round(deuda_pm*100/saldo_pm, 2)
        growth_porc_deuda = porc_deuda_actual - porc_deuda_pm

        trans_df_base = data['transacciones']
        trans_df_base['Mes_Año_dt'] = pd.to_datetime(trans_df_base['Mes_Año'], format='%b-%Y')
        trans_df = trans_df_base[trans_df_base['Mes_Año_dt'] == trans_df_base['Mes_Año_dt'].max()]
        max_date = trans_df['Mes_Año'].max()

        with col1:
            st.metric(f"Patrimonio", f"€{saldo_actual:,.2f}", str(round(growth_saldo, 2)) + '%')
        with col2:
            st.metric(f"Deuda", f"€{deuda_actual:,.2f}", str(round(growth_deuda, 2)) + '%', 'inverse')
        with col3:
            st.metric(f"Endeudamiento", f"{porc_deuda_actual:,.2f}%", str(round(growth_porc_deuda, 2)) + '%', 'inverse')
    if 'inversiones' in data and not data['inversiones'].empty:
        inv_df = data['inversiones']
        inversiones_actual = inv_df.groupby('Fecha')['Valor Actual'].sum().iloc[-1] if not inv_df.empty else 0
        inversiones_lm = inv_df.groupby('Fecha')['Valor Actual'].sum().iloc[-2] if not inv_df.empty else 0
        inversiones_compra = inv_df.groupby('Fecha')['Valor Compra'].sum().iloc[-1] if not inv_df.empty else 0
        renta_variable = inv_df[inv_df['Categoría'] == 'Renta Variable'].groupby('Fecha')['Valor Actual'].sum().iloc[-1] if not inv_df.empty else 0
        renta_variable_lm = inv_df[inv_df['Categoría'] == 'Renta Variable'].groupby('Fecha')['Valor Actual'].sum().iloc[-2] if not inv_df.empty else 0
        prc_renta_variable = renta_variable * 100 / inversiones_actual
        prc_renta_variable_lm = renta_variable_lm * 100 / inversiones_lm
        growth_renta_variable = prc_renta_variable - prc_renta_variable_lm
        rentabilidad = (inversiones_actual - inversiones_compra) * 100 / inversiones_compra

        prc_invertido = inversiones_actual * 100 / saldo_actual
        prc_invertido_lm = inversiones_lm * 100 / saldo_pm
        growth_invertido = prc_invertido - prc_invertido_lm


        # Métricas principales
        col1, col2 = st.columns(2)

        trans_df_base = data['inversiones']
        trans_df_base['Mes_Año'] = trans_df_base['Fecha'].dt.strftime('%b-%Y')
        trans_df_base['Mes_Año_dt'] = pd.to_datetime(trans_df_base['Mes_Año'], format='%b-%Y')

        trans_df = trans_df_base[trans_df_base['Mes_Año_dt'] == trans_df_base['Mes_Año_dt'].max()]
        max_date = trans_df['Mes_Año'].max()

        with col4:
            st.metric(f"Inversión Actual", f"€{inversiones_actual:,.2f}", str(round(rentabilidad, 2)) + '%')
        with col5:
            st.metric(f"Patrimonio Invertido",
                      f"{prc_invertido:,.2f}%", str(round(growth_invertido, 2)) + '%')

def create_balance_chart(df):
    if df is None or df.empty:
        return None

    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.45)

    fig = px.area(
        df,
        x='Fecha',
        y='Valor',
        color='Nombre',
        title='Distribución del patrimonio',
        markers=True
    )

    # -------------------------------
    # ✅ 1. Calcular total por fecha
    # -------------------------------
    total_df = df.groupby("Fecha", as_index=False)["Valor"].sum()

    # -------------------------------
    # ✅ 2. Añadir anotaciones (labels)
    # -------------------------------
    for _, row in total_df.iterrows():
        fig.add_annotation(
            x=row["Fecha"],
            y=row["Valor"],
            text=str(int(row["Valor"])),    # cambia a round(...) si quieres decimales
            showarrow=False,
            font=dict(color="white", size=12),
            yshift=10                       # separa el label del área
        )

    # -------------------------------
    #  Layout (tu código original)
    # -------------------------------
    fig.update_layout(
        autosize=True,
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        font=dict(color="white"),
        height=350,
        title=dict(font=dict(color="white"), y=1, yanchor="top"),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            title=None,
            font=dict(color="white")
        )
    )
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig

def categorias_pie_chart(df):
    if df is None or df.empty:
        return None

    # Ensure Fecha is datetime
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # ➤ Filter to last month in the dataset
    last_month = df["Fecha"].max()
    df_last = df[df["Fecha"] == last_month]

    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.45)

    # Aggregate by category
    pie_df = df_last.groupby("Categoría", as_index=False)["Valor"].sum()

    fig = px.pie(
        pie_df,
        names="Categoría",
        values="Valor",
        title=f"Distribución por categoría — {last_month.date()}",
        hole=0.45
    )

    fig.update_layout(
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        font=dict(color="white"),
        height=350,
        title=dict(font=dict(color="white")),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            title=None,
            font=dict(color="white")
        )
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig

def create_investment_chart(df):
    """
    Crea gráfico de evolución de inversiones
    """
    if df is None or df.empty:
        return None

    df_grouped = (
        df.groupby("Fecha")[["Valor Actual", "Valor Compra"]]
        .sum()
        .reset_index()
    )
    fig = px.line(df_grouped, x='Fecha', y=['Valor Actual', 'Valor Compra'],
                  markers=True, title='Evolución de las inversiones vs valor de compra')

    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.4)
    fig.update_layout(
        autosize=True,
        plot_bgcolor="#0f172a",  # chart area
        paper_bgcolor="#0f172a",  # outer area
        font=dict(color="white"),
        height=350,
        title=dict(
            font=dict(
                color="white"  # font color
            ),
            y=0.97,          # <--- mueve el título más cerca del gráfico
            yanchor="top"    # ancla desde arriba
        ),
        # Legend config
        legend=dict(
            orientation="h",  # horizontal
            yanchor="top",  # anchor legend to top of its box
            y=-0.2,  # move it below the chart
            xanchor="center",
            x=0.5,
            title=None,  # remove legend title
            font=dict(color="white")  # legend text color
        )
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0)
    )

    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return fig