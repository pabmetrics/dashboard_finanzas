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

from visuals import *


warnings.filterwarnings('ignore')


# Page config
load_page_config()

# Sidebar and data load
data = load_sidebar()

if data:
    col = st.columns((1.5, 2, 2), gap='medium')
    with col[0]:
        load_summary_kpis(data)
        fig1, fig2 = create_transactions_charts(data['transacciones'])
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
    with col[1]:
        fig3 = create_balance_chart(data['saldos'])
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
        load_saldo_kpis(data)
        debt_fig = create_debt_chart(data['deudas'])
        if debt_fig:
            st.plotly_chart(debt_fig, width='stretch')

    with col[2]:
        load_investment_kpis(data)
        inv_fig = create_investment_chart(data['inversiones'])
        if inv_fig:
            st.plotly_chart(inv_fig, width='stretch')
        budget_fig = create_budget_analysis(data)
        if budget_fig:
            st.plotly_chart(budget_fig, width='stretch')
else:
    st.info("👆 Sube tu archivo Excel en el menu lateral para comenzar el análisis")
