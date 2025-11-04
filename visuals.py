
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

def load_page_config():
    with open('style.css') as f:
        st.sidebar.markdown(f'<style> {f.read()} </style>', unsafe_allow_html = True)

    st.set_page_config(
        page_title="Mi Dashboard de finanzas",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded")

def load_sidebar():
    # Sidebar para carga de archivo
    st.sidebar.header("📁 Cargar Datos")
    uploaded_file = st.sidebar.file_uploader(
        "Selecciona tu archivo Excel de finanzas",
        type=['xlsx', 'xls'],
        help="El archivo debe contener las hojas: Transacciones, Presupuesto, Saldos, Deudas, Inversiones"
    )
    screen_height = streamlit_js_eval(label="screen.height", js_expressions='screen.height')
    if screen_height:
        st.session_state["vh"] = screen_height




    if uploaded_file is not None:
        with st.spinner('Procesando archivo...'):
            data = load_and_process_data(uploaded_file)

        if data:
            st.sidebar.success("✅ Archivo cargado exitosamente!")
            return data
        # Button to re-render

def load_summary_kpis(data):
    if 'transacciones' in data and not data['transacciones'].empty:


        trans_df_base = data['transacciones']

        trans_df_base['Mes_Año_dt'] = pd.to_datetime(trans_df_base['Mes_Año'], format='%b-%Y')

        trans_df = trans_df_base[trans_df_base['Mes_Año_dt'] == trans_df_base['Mes_Año_dt'].max()]
        max_date = trans_df['Mes_Año'].max()

        st.markdown(f"<span style='color:white'>Fecha evaluada: {max_date}</span>", unsafe_allow_html=True)
        prev_m = trans_df_base['Mes_Año_dt'].max() - relativedelta(months=1)
        trans_df_prev = trans_df_base[trans_df_base['Mes_Año_dt'] == prev_m]
        # Métricas principales
        col1, col2 = st.columns(2)
        ingresos_total = trans_df[trans_df['Importe'] > 0]['Importe'].sum()
        ingresos_prev = trans_df_prev[trans_df_prev['Importe'] > 0]['Importe'].sum()
        growth_ingresos = (ingresos_total - ingresos_prev) * 100/ingresos_prev

        gastos_total = abs(trans_df[trans_df['Importe'] < 0]['Importe'].sum())
        gastos_prev = abs(trans_df_prev[trans_df_prev['Importe'] < 0]['Importe'].sum())
        growth_gastos = (gastos_total - gastos_prev) * 100 / gastos_prev

        porcentaje_ahorro = (ingresos_total - gastos_total) * 100 / ingresos_total
        porcentaje_ahorro_prev = (ingresos_prev - gastos_prev) * 100 / ingresos_prev
        growth_ahorro = porcentaje_ahorro - porcentaje_ahorro_prev

        balance_neto = ingresos_total - gastos_total
        balance_neto_prev = ingresos_prev - gastos_prev
        growth_balance = (balance_neto - balance_neto_prev) * 100 / balance_neto_prev

        with col1:
            st.metric(f"Ingresos Totales", f"€{ingresos_total:,.2f}", str(round(growth_ingresos, 2)) + '%')
        with col2:
            st.metric(f"Gastos Totales", f"€{gastos_total:,.2f}", str(round(growth_gastos, 2)) + '%', 'inverse')
        with col1:
            st.metric(f"Balance Neto", f"€{balance_neto:,.2f}", str(round(growth_balance, 2)) + '%')
        with col2:
            st.metric(f"Porcentaje de ahorro", f"{porcentaje_ahorro:,.2f} %", str(round(growth_ahorro, 2)) + '%')

def load_investment_kpis(data):
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


        # Métricas principales
        col1, col2 = st.columns(2)

        trans_df_base = data['inversiones']
        trans_df_base['Mes_Año'] = trans_df_base['Fecha'].dt.strftime('%b-%Y')
        trans_df_base['Mes_Año_dt'] = pd.to_datetime(trans_df_base['Mes_Año'], format='%b-%Y')

        trans_df = trans_df_base[trans_df_base['Mes_Año_dt'] == trans_df_base['Mes_Año_dt'].max()]
        max_date = trans_df['Mes_Año'].max()

        with col1:
            st.metric(f"Inversión Actual", f"€{inversiones_actual:,.2f}", str(round(rentabilidad, 2)) + '%')
        with col2:
            st.metric(f"Renta variable", f"{prc_renta_variable:,.2f}%", str(round(growth_renta_variable, 2)) + '%')



def load_saldo_kpis(data):
    if 'saldos' in data and not data['saldos'].empty:
        saldos_df = data['saldos']

        # Métricas principales
        col1, col2, col3 = st.columns(3)
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


def create_transactions_charts(df):
    """
    Crea gráficos para el análisis de transacciones
    """
    if df is None or df.empty:
        return None, None, None, None

    # Agregar columna de mes-año para agrupación
    df['Mes_Año'] = df['Fecha'].dt.strftime('%b-%Y').astype(str)

    # Gráfico 1: Ingresos vs Gastos por mes
    monthly_summary = df.groupby(['Mes_Año', 'Tipo'])['Importe'].sum().reset_index()
    monthly_summary['Importe'] = monthly_summary['Importe'].abs()
    monthly_summary['Mes_Año_dt'] = pd.to_datetime(monthly_summary['Mes_Año'], format='%b-%Y')
    monthly_summary = monthly_summary.sort_values('Mes_Año_dt')
    fig1 = px.bar(monthly_summary, x='Mes_Año', y='Importe', color='Tipo',
                  barmode='group', title = 'Evolución de Ingesos vs Gastos')

    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.35)
    fig1.update_layout(
        autosize=True,
        plot_bgcolor="#0f172a",  # chart area
        paper_bgcolor="#0f172a",  # outer area
        font = dict(color="white"),
        height = chart_height,
        title=dict(
            font=dict(
                color="white"
            ),
            y=0.82,          # <--- mueve el título más cerca del gráfico
            yanchor="top"    # ancla desde arriba
        ),
            # Legend config
        legend = dict(
            orientation="h",  # horizontal
            yanchor="top",  # anchor legend to top of its box
            y=-0.2,  # move it below the chart
            xanchor="center",
            x=0.5,
            title=None,  # remove legend title
            font=dict(color="white")  # legend text color
        )
    )
    fig1.update_xaxes(title=None)
    fig1.update_yaxes(title=None)

    # Gráfico 2: Gastos por categoría
    gastos_df = df[df['Tipo'] == 'Gasto'] if 'Tipo' in df.columns else df[df['Importe'] < 0]
    if not gastos_df.empty:
        gastos_df['Mes_Año_dt'] = pd.to_datetime(gastos_df['Mes_Año'], format='%b-%Y')
        gastos_f_df = gastos_df[gastos_df['Mes_Año_dt'] == gastos_df['Mes_Año_dt'].max()]
        max_date = gastos_f_df['Mes_Año'].max()
        gastos_categoria = gastos_f_df.groupby('Categoria')['Importe'].sum().abs().reset_index()
        fig2 = px.bar(gastos_categoria, x='Importe', y='Categoria', orientation='h', title = f'Distribución de gastos')
        fig2.update_layout(
            autosize=True,
            plot_bgcolor="#0f172a",  # chart area
            paper_bgcolor="#0f172a",  # outer area
            font=dict(color="white"),
            title=dict(
                font=dict(
                    color="white"  # font color
                ),
                y=0.82,          # <--- mueve el título más cerca del gráfico
                yanchor="top"    # ancla desde arriba
            ),
            height=chart_height,
            # Legend config
            showlegend=False
        )
        fig2.update_xaxes(title=None)
        fig2.update_yaxes(title=None)
    else:
        fig2 = None

    return fig1, fig2

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
        height=chart_height,
        title=dict(font=dict(color="white"), y=0.82, yanchor="top"),
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

    return fig



def create_debt_chart(df):
    """
    Crea gráfico de evolución de deudas
    """
    if df is None or df.empty:
        return None
    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.45)
    fig = px.bar(df, x='Fecha', y='Valor', color='Nombre', title = 'Evolución de la deuda')
    fig.update_layout(
        autosize=True,
        plot_bgcolor="#0f172a",  # chart area
        paper_bgcolor="#0f172a",  # outer area
        font=dict(color="white"),
        title=dict(
            font=dict(
                color="white"  # font color
            ),
            y=0.82,          # <--- mueve el título más cerca del gráfico
            yanchor="top"    # ancla desde arriba
        ),
        height=chart_height,
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
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
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
        height=chart_height,
        title=dict(
            font=dict(
                color="white"  # font color
            ),
            y=0.82,          # <--- mueve el título más cerca del gráfico
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
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return fig


def create_budget_analysis(data):
    trans_df = data['transacciones']
    presup_df = data['presupuesto']
    trans_df['Mes_Año_dt'] = pd.to_datetime(trans_df['Mes_Año'], format='%b-%Y')
    presup_df['Mes_Año_dt'] = pd.to_datetime(presup_df['Mes_Año'], format='%b-%Y')
    trans_f_df = trans_df[trans_df['Mes_Año_dt'] == trans_df['Mes_Año_dt'].max()]
    presup_f_df = presup_df[presup_df['Mes_Año_dt'] == trans_df['Mes_Año_dt'].max()]
    presup = presup_f_df.groupby(['Mes_Año', 'Categoria'])['Valor'].sum().to_frame()
    presup = presup.rename(columns={"Valor": "Presupuesto"})
    trans = trans_f_df.groupby(['Mes_Año', 'Categoria'])['Importe'].sum().to_frame()
    trans = trans.rename(columns={"Importe": "Real"})
    df = pd.merge(presup, trans, on=['Mes_Año', 'Categoria'])

    max_date = trans_f_df['Mes_Año'].max()
    # Resumen por categoría
    budget_summary = (
        df.groupby("Categoria")[["Presupuesto", "Real"]]
        .sum()
        .reset_index()
    )


    fig1 = px.bar(budget_summary, x=['Presupuesto', 'Real'], y='Categoria', orientation='h', barmode= 'group', title=f'Cumplimiento del presupuesto por categoría')

    container_height = st.session_state.get("container_height", 800)
    chart_height = int(container_height * 0.48)
    fig1.update_layout(
        autosize=True,
        plot_bgcolor="#0f172a",  # chart area
        paper_bgcolor="#0f172a",  # outer area
        font=dict(color="white"),
        height=chart_height,
        title=dict(
            font=dict(
                color="white"  # font color
            ),
            y=0.82,          # <--- mueve el título más cerca del gráfico
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

    fig1.update_xaxes(title=None)
    fig1.update_yaxes(title=None)

    return fig1