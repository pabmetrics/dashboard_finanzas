
# Sidebar para carga de archivo
st.sidebar.header("📁 Cargar Datos")
uploaded_file = st.sidebar.file_uploader(
    "Selecciona tu archivo Excel de finanzas",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: Transacciones, Presupuesto, Saldos, Deudas, Inversiones"
)


if uploaded_file is not None:
    with st.spinner('Procesando archivo...'):
        data = load_and_process_data(uploaded_file)

    if data:
        st.success("✅ Archivo cargado exitosamente!")

        # Crear tabs para diferentes secciones
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Resumen", "💳 Transacciones", "💰 Saldos",
            "📈 Inversiones", "💸 Deudas", "📋 Presupuesto"
        ])

        with tab1:

            # Calcular métricas si hay datos disponibles
            if 'transacciones' in data and not data['transacciones'].empty:

                trans_df_base = data['transacciones']
                trans_df_base['Mes_Año_dt'] = pd.to_datetime(trans_df_base['Mes_Año'], format='%b-%Y')
                monthly_summary = trans_df_base.sort_values('Mes_Año_dt')

                trans_df = trans_df_base[trans_df_base['Mes_Año_dt'] == trans_df_base['Mes_Año_dt'].max()]

                max_date = trans_df['Mes_Año'].max()
                st.header(f"📊 Resumen Financiero [{max_date}]")

                # Métricas principales
                col1, col2, col3, col4, col5 = st.columns(5)
                ingresos_total = trans_df[trans_df['Importe'] > 0]['Importe'].sum()
                gastos_total = abs(trans_df[trans_df['Importe'] < 0]['Importe'].sum())
                porcentaje_ahorro = (ingresos_total - gastos_total) * 100 / ingresos_total
                balance_neto = ingresos_total - gastos_total


                with col1:
                    st.metric("Ingresos Totales", f"€{ingresos_total:,.2f}")
                with col2:
                    st.metric("Gastos Totales", f"€{gastos_total:,.2f}")
                with col3:
                    st.metric("Balance Neto", f"€{balance_neto:,.2f}")
                with col4:
                    st.metric("Porcentaje de ahorro", f"{porcentaje_ahorro:,.2f} %")

            if 'saldos' in data and not data['saldos'].empty:
                saldos_df = data['saldos']
                saldo_actual = saldos_df.groupby('Fecha')['Valor'].sum().iloc[-1] if not saldos_df.empty else 0
                with col5:
                    st.metric("Saldo Total Actual", f"€{saldo_actual:,.2f}")

            # Gráficos de resumen
            if 'transacciones' in data:
                fig1, fig2, fig3, fig4 = create_transactions_charts(data['transacciones'])
                if fig1:
                    st.plotly_chart(fig1, width='stretch')
                fig1, fig2, fig3, fig4 = create_transactions_charts(trans_df)
                if fig4:
                    st.plotly_chart(fig4, width='stretch')

        with tab2:
            st.header("💳 Análisis de Transacciones")
            if 'transacciones' in data and not data['transacciones'].empty:
                trans_df = data['transacciones']

                # Filtros
                col1, col2 = st.columns(2)
                with col1:
                    categorias = st.multiselect("Filtrar por categoría",
                                                trans_df['Categoria'].unique(),
                                                default=trans_df['Categoria'].unique())
                with col2:
                    mes_filter = st.multiselect(
                        "Selecciona Mes/Año:",
                        options=trans_df_base["Mes_Año"].unique(),
                        default=trans_df_base["Mes_Año"].unique()
                    )

                # Aplicar filtros
                filtered_df = trans_df[
                    (trans_df['Categoria'].isin(categorias))
                    ]

                filtered_df = filtered_df[filtered_df["Mes_Año"].isin(mes_filter)]

                # Gráficos

                #t_fig1, t_fig2, t_fig3, t_fig4 = create_transactions_charts(filtered_df)

                #col1, col2 = st.columns(2)
                #with col1:
                #    if t_fig1:
                #        st.plotly_chart(t_fig1, width='stretch')
                #with col2:
                #    if t_fig2:
                #        st.plotly_chart(t_fig2, width='stretch')

                #col1, col2 = st.columns(2)
                #with col1:
                #    if t_fig3:
                #        st.plotly_chart(t_fig3, width='stretch')
                #with col2:
                #    if t_fig4:
                #        st.plotly_chart(t_fig4, width='stretch')

                # Tabla de transacciones
                st.subheader("Detalle de Transacciones")
                st.dataframe(filtered_df, width='stretch')
            else:
                st.info("No hay datos de transacciones disponibles")

        with tab3:
            st.header("💰 Evolución de Saldos")
            col1, col2, col3 = st.columns(3)

            if 'saldos' in data and not data['saldos'].empty:
                saldos_df = data['saldos']
                saldo_actual = saldos_df.groupby('Fecha')['Valor'].sum().iloc[-1] if not saldos_df.empty else 0
                saldo_pm = saldos_df.groupby('Fecha')['Valor'].sum().iloc[-2] if not saldos_df.empty else 0
                cuentas = saldos_df.groupby('Fecha')['Nombre'].count().iloc[-1] if not saldos_df.empty else 0
                crec_pm = (saldo_actual - saldo_pm)*100/saldo_pm
                with col1:
                    st.metric("Saldo Total Actual", f"€{saldo_actual:,.2f}")
                with col2:
                    st.metric("Saldo Total PM", f"{crec_pm:,.2f}%")
                with col3:
                    st.metric("Número de cuentas activas", f"{cuentas}")

            if 'saldos' in data and not data['saldos'].empty:
                saldos_fig = create_balance_chart(data['saldos'])
                if saldos_fig:
                    st.plotly_chart(saldos_fig, width='stretch')

                # Tabla resumen
                st.subheader("Saldos Actuales")
                ultimo_periodo = data['saldos']['Fecha'].max()
                saldos_actuales = data['saldos'][data['saldos']['Fecha'] == ultimo_periodo]
                st.dataframe(saldos_actuales, width='stretch')
            else:
                st.info("No hay datos de saldos disponibles")

        with tab4:

            st.header("📈 Análisis de Inversiones")
            if 'inversiones' in data and not data['inversiones'].empty:
                inv_df = data['inversiones']
                inversiones_actual = inv_df.groupby('Fecha')['Valor Actual'].sum().iloc[-1] if not inv_df.empty else 0
                inversiones_compra = inv_df.groupby('Fecha')['Valor Compra'].sum().iloc[-1] if not inv_df.empty else 0
                renta_variable = inv_df[inv_df['Categoría'] == 'Renta Variable'].groupby('Fecha')['Valor Actual'].sum().iloc[-1] if not inv_df.empty else 0
                prc_renta_variable = renta_variable * 100 / inversiones_actual
                rentabilidad = (inversiones_actual - inversiones_compra) * 100 / inversiones_compra
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Cartera Actual", f"€{inversiones_actual:,.2f}")
                with col2:
                    st.metric("Rentabilidad Acumulada", f"{rentabilidad:,.2f} %")
                with col3:
                    st.metric("Porcentaje de Renta Variable", f"{prc_renta_variable:,.2f} %")


                inv_fig = create_investment_chart(data['inversiones'])
                if inv_fig:
                    st.plotly_chart(inv_fig, width='stretch')

                st.subheader("Detalle de Inversiones")
                inv_tabla_df = (
                    inv_df[inv_df['Fecha'] == inv_df['Fecha'].max()].groupby(['Nombre', 'Tipo de Activo', 'Categoría'])[['Valor Compra', 'Valor Actual']]
                    .sum()
                )
                inv_tabla_df['Rentabilidad'] = (
                        ((inv_tabla_df['Valor Actual'] - inv_tabla_df['Valor Compra'])
                         / inv_tabla_df['Valor Compra'])
                        .round(4)
                )

                inv_tabla_df['Valor Actual'] = inv_tabla_df['Valor Actual'].round(2)
                inv_tabla_df.drop(columns=["Valor Compra"], axis=1, inplace=True)
                st.dataframe(
                    inv_tabla_df.style.format({
                        "Valor Actual": "{:,.2f}€",  # 2 decimales con separador de miles
                        "Rentabilidad": "{:.2%}"  # formato porcentaje
                    })
                )
            else:
                st.info("No hay datos de inversiones disponibles")

        with tab5:
            st.header("💸 Análisis de Deudas")

            col1, col2, col3 = st.columns(3)
            deuda_actual = data['deudas'].groupby('Fecha')['Valor'].sum().iloc[-1] if not data['deudas'].empty else 0
            deuda_pm = data['deudas'].groupby('Fecha')['Valor'].sum().iloc[-2] if not data['deudas'].empty else 0
            variacion = (deuda_actual - deuda_pm) * 100 / deuda_pm
            saldo_actual = data['saldos'].groupby('Fecha')['Valor'].sum().iloc[-1] if not data['saldos'].empty else 0
            deuda_saldo = deuda_actual * 100/saldo_actual
            with col1:
                st.metric("Deuda Actual", f"€{deuda_actual:,.2f}")
            with col2:
                st.metric("Variación último mes", f"{variacion:,.2f} %")
            with col3:
                st.metric("Deuda vs Saldo", f"{deuda_saldo:,.2f} %")

            if 'deudas' in data and not data['deudas'].empty:
                debt_fig = create_debt_chart(data['deudas'])
                if debt_fig:
                    st.plotly_chart(debt_fig, width='stretch')

                deudas_df = data['deudas'][data['deudas']['Fecha'] == data['deudas']['Fecha'].max()]
                st.subheader("Detalle de Deudas")
                st.dataframe(deudas_df, width='stretch')
            else:
                st.info("No hay datos de deudas disponibles")

        with tab6:
            st.header("📋 Análisis de Presupuesto")

            col1, col2, col3 = st.columns(3)

            max_date = data['transacciones']['Mes_Año'].max()
            presup_df = data['presupuesto']
            presup_gasto_df = presup_df[
                (presup_df['Mes_Año'] == max_date) & (presup_df['Tipo'] == 'Ingreso')
                ]
            print(presup_gasto_df)
            presupuesto_gastos_actual = presup_df.groupby('Fecha')['Valor'].sum().iloc[-1] if not presup_df.empty else 0
            deuda_pm = data['transacciones'].groupby('Fecha')['Valor'].sum().iloc[-1] if not data['deudas'].empty else 0
            variacion = (deuda_actual - deuda_pm) * 100 / deuda_pm
            saldo_actual = data['saldos'].groupby('Fecha')['Valor'].sum().iloc[-1] if not data['saldos'].empty else 0
            deuda_saldo = deuda_actual * 100 / saldo_actual
            with col1:
                st.metric("Deuda Actual", f"€{deuda_actual:,.2f}")
            with col2:
                st.metric("Variación último mes", f"{variacion:,.2f} %")
            with col3:
                st.metric("Deuda vs Saldo", f"{deuda_saldo:,.2f} %")


            presup = data['presupuesto'].groupby(['Mes_Año', 'Categoria'])['Valor'].sum().to_frame()
            presup = presup.rename(columns = {"Valor" : "Presupuesto"})
            trans = data['transacciones'].groupby(['Mes_Año', 'Categoria'])['Importe'].sum().to_frame()
            trans = trans.rename(columns={"Importe": "Real"})
            df_merge = pd.merge(presup, trans, on = ['Mes_Año', 'Categoria'])




            if 'presupuesto' in data and not data['presupuesto'].empty:
                fig1, fig2, fig3 = create_budget_analysis(df_merge)
                if fig1:
                    st.plotly_chart(fig1, width='stretch')
                if fig2:
                    st.plotly_chart(fig2, width='stretch')
                if fig3:
                    st.plotly_chart(fig3, width='stretch')

                st.subheader("Detalle del Presupuesto")
                st.dataframe(data['presupuesto'], width='stretch')
            else:
                st.info("No hay datos de presupuesto disponibles")

    else:
        st.error("❌ Error al procesar el archivo. Verifica que tenga el formato correcto.")

else:
    st.info("👆 Sube tu archivo Excel para comenzar el análisis")

    # Mostrar información sobre el formato esperado
    st.markdown("### 📋 Formato esperado del archivo Excel")

    with st.expander("Ver estructura de las hojas"):
        st.markdown("""
        **Hoja 'Transacciones':**
        - Fecha, Categoria, Nombre, Tipo, Importe, Cuenta

        **Hoja 'Presupuesto':**
        - Cuenta, Categoria, Tipo, sep-25, oct-25, nov-25, dic-25

        **Hoja 'Saldos':**
        - Nombre, Tipo de Cuenta, dic-24, ene-25, feb-25, mar-25, abr-25, may-25, jun-25, jul-25, ago-25, sep-25, oct-25, nov-25, dic-25

        **Hoja 'Deudas':**
        - Nombre, Tipo de Deuda, dic-24, ene-25, feb-25, mar-25, abr-25, may-25, jun-25, jul-25, ago-25, sep-25, oct-25, nov-25, dic-25

        **Hoja 'Inversiones':**
        - Tipo de Activo, Nombre, Categoría, sep-25, oct-25, nov-25, dic-25
        """)

# Footer
st.markdown("---")
st.markdown(
    "💡 **Tip:** La aplicación detecta automáticamente las columnas de fechas. Puedes usar cualquier cantidad de meses y diferentes formatos de fecha.")