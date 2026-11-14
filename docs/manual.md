# Manual de uso

## La idea

La app junta en un sitio todo lo que tienes: cuentas, inversiones, crowdfunding y otros activos. Con eso calcula tu patrimonio mes a mes. Los datos le llegan de tres formas:

1. **Importando extractos** de bancos y brókers (pestaña *Importar*).
2. **Metiendo un dato a mano** en los activos sin extracto: efectivo, Pluxee, Bleap, Cartera Rock, Equito, Urbanitae…
3. **Tu Excel antiguo**, ya cargado, que da el histórico hasta ahora.

Cada cuenta enseña su valor según **el último dato que tiene**. Si ese dato tiene más de 35 días, sale un ⚠️ en la lista: toca actualizarla.

## Los imports: ¿mensuales o históricos?

**Las dos cosas valen.** Un extracto puede cubrir el periodo que quieras: un mes, un año o desde el principio.

- **No se duplica nada.** Cada movimiento tiene una huella. Si subes dos veces el mismo archivo, o dos archivos que se solapan (enero-marzo y luego febrero-abril), lo repetido se ignora y solo entra lo nuevo.
- **Puedes subirlos en cualquier orden.** La app ordena por fecha.
- **Recomendación:**
  - **Una vez**: carga histórica, con un extracto lo más largo posible de cada banco y bróker.
  - **Cada mes** (por ejemplo, el día 1): un extracto del mes anterior de cada sitio. Con 5 minutos al mes basta.

### Qué hace cada import

| Origen | Qué descargar | Qué saca la app |
|---|---|---|
| **XTB** | Informe completo en Excel, con el rango de fechas más amplio | Compras, ventas, dividendos e intereses, y el **precio del día del informe** de lo que tienes. El informe trae todo el historial, así que basta el último. |
| **Fondos (Inversis)** | En MyInvestor, las operaciones de fondos de Inversis (`.xls`) | Suscripciones, reembolsos y traspasos con su precio. |
| **BBVA** | Excel de movimientos. Elige a qué cuenta BBVA corresponde | Movimientos (gastos e ingresos) y saldo. |
| **Revolut** | CSV de movimientos | Movimientos y saldo. |
| **Cuenta MyInvestor** | CSV de movimientos | Movimientos. El extracto **no trae saldo**: la app lo calcula sumando todos los movimientos guardados (ver abajo). |
| **Urbanitae** | Excel "Mis inversiones" | Capital vivo, la suma de los proyectos no terminados. Opcional: también puedes meterlo a mano. |

### El saldo de la Cuenta MyInvestor

El saldo es la **suma de todos los movimientos guardados**, empezando en 0. Así que:

- Si en algún momento subes el histórico **desde la apertura de la cuenta**, cuadra solo. Después, cada mes, basta con subir el mes nuevo (o todo otra vez: no se duplica).
- El campo *Saldo final* es **opcional**. Solo hace falta si lo guardado no empieza en la apertura: escribe el saldo real tras el último movimiento del archivo, una vez, y la app lo guarda como referencia para cuadrar el resto.
- Tras importar, la app enseña el *saldo calculado*. Si no coincide con el de MyInvestor, falta algún movimiento o hace falta la referencia.

### Extractos frente a Excel antiguo

En cuanto una cuenta tiene extracto, manda el extracto. El Excel antiguo solo se usa para las fechas anteriores al primer movimiento importado.

### Qué pasa con los precios

**Se actualizan solos cada día**, con los precios de cierre de Yahoo Finance: los fondos por ISIN y las acciones y ETF por ticker, todo pasado a euros. La primera vez se descarga también el histórico, así que la evolución mensual sale con precios reales.

- El valor de fondos y acciones es **títulos × último precio**. Debajo de cada posición aparece la fecha del precio. Los fondos publican su valor con 1-2 días de retraso.
- Antes de usar un precio automático, la app lo compara con el de tus operaciones reales. Si se desvía más de un 10 %, no lo usa y avisa ("Sin precio automático: …"). En ese caso se queda con el último precio conocido.
- Los precios de tus operaciones y de los informes de XTB mandan sobre los automáticos del mismo día.
- En *Inversiones*, abajo, se ve cuándo se actualizaron por última vez y hay un botón para **actualizar ahora**.

## Datos a mano

### Otros activos (efectivo, Pluxee, Bleap, Cartera Rock…)
Entra en el activo → **Actualizar valor** → fecha y valor → Guardar. Cada dato queda guardado, así que se ve su evolución.

### Crowdfunding (Equito, Urbanitae)
Entra en el activo → **Dato del mes**:
- **Valor**: lo que tienes invertido ahora mismo en la plataforma, según su panel.
- **Rentas cobradas**: lo que te han pagado ese mes (alquileres o intereses), en total, sin separar por proyecto. Déjalo vacío si no has cobrado nada.

Las rentas **no suben el valor**: se suman aparte como *rentas cobradas*, para que veas cuánto rinde la plataforma.

### Crear un activo nuevo
En *Patrimonio*, abajo del todo → **Añadir activo**. Elige el tipo:
- **Otro activo**: efectivo, saldo en otra plataforma, un depósito… Elige también si es Liquidez, Renta Variable o Renta Fija para el reparto.
- **Crowdfunding**: otra plataforma como Equito.
- **Cuenta bancaria**: una cuenta sin import, en la que pondrás el saldo a mano.
- **Deuda**: préstamos o tarjetas. Pon el importe pendiente en positivo y la app lo resta del patrimonio.

## Inversiones

La pestaña *Inversiones* junta todo lo invertido: brókers, crowdfunding y activos manuales de renta fija o variable.

- **Ganancia**: valor actual − lo aportado (+ las rentas del crowdfunding, que se cobran fuera). El % es sobre lo aportado.
- **Este mes**: lo que han ganado o perdido tus inversiones este mes, **sin contar** el dinero nuevo que has metido.
- **Latente**: ganancia de lo que tienes ahora, sin vender. **Realizada**: la de lo ya vendido. **Cobrado**: dividendos, intereses y rentas, netos de retenciones.
- **Valor frente a aportado**: la distancia entre las dos líneas es tu ganancia.
- **Posiciones**: con su peso y su rentabilidad. Tócalas para ver el detalle.

### Fondo de emergencia y plan de reparto

El plan tiene dos bloques, como la hoja *Plan* del Excel:

1. **Fondo de emergencia** (por ejemplo, 15.000 €: 1/3 en liquidez y 2/3 en fondo monetario). Se ve aparte, con lo que está cubierto y lo que falta.
2. **Resto del patrimonio**: todo lo demás, una vez apartado el fondo de emergencia. Se compara con los porcentajes del plan, y para cada tipo se dice **cuánto falta o sobra en €**. "Cuenta corriente" es la liquidez que sobra fuera del fondo de emergencia.

**Editar plan** (en las tarjetas del plan):
- Cambiar el importe del fondo de emergencia, los tipos y sus porcentajes. Cada bloque debe sumar 100 %.
- **Qué es cada activo**: a qué tipo del plan pertenece cada cosa que tienes (o crear un tipo nuevo) y si cuenta como Renta Variable, Renta Fija o Liquidez. Se guarda al cambiarlo.

## Gastos

La pestaña *Gastos* usa los movimientos de los bancos importados:
- **Las transferencias entre tus cuentas no cuentan** como gasto ni como ingreso.
- Las categorías salen de **reglas**: si el concepto contiene "mercadona", va a Alimentación.
- Para corregir o enseñar una regla, **toca el movimiento**, ajusta el texto ("cuando el concepto contenga…") y elige la categoría. Se aplica a todos los movimientos que encajan, los de ahora y los que importes después.
- Para movimientos entre tus cuentas o hacia tus brókers, usa **Transferencia interna** o **Inversión**. Así no cuentan como gasto.

## De dónde sale cada número

- **Patrimonio neto**: suma del último valor de todas las cuentas, menos las deudas.
- **Este mes**: diferencia con el patrimonio a final del mes anterior.
- **Invertido**: valor de brókers y crowdfunding.
- **Ganancia inv.**: valor actual menos lo aportado neto (aportaciones menos retiradas). En el crowdfunding no hay ganancia latente, porque se valora a lo invertido.
- **Fondo de emergencia / Resto vs. plan**: ver *Inversiones*. En naranja, lo que se desvía 3 puntos o más.
- **Evolución**: valor a fin de cada mes. Los meses anteriores a tener extractos salen del Excel antiguo, que tenía una foto por mes, así que alguno puede verse raro (por ejemplo, abril-mayo de 2026). Se corrige al cargar el histórico de los bancos.

## Si algo falla

- **No carga la app**: comprueba que Tailscale está activado en el móvil.
- **Un import da error**: probablemente el archivo no es el esperado (otro formato u otra pestaña del banco). Pásaselo al agente para que lo mire.
