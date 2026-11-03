# Bot de Now Football

Publica solo en la página de Facebook **Now Football**, cada 2 horas,
las mejores imágenes de @NFL_Stats, @polymarketblitz y @SleeperNFL,
convertidas a formato 4:5 con tu logo. Nunca repite una imagen.

## No necesitas saber programar

Todo se maneja con cuatro botones dentro de GitHub, en la pestaña **Actions**:

| Botón | Qué hace |
|---|---|
| **1. Revisar que todo esté bien** | Diagnóstico. Te dice en español si algo falla. No publica nada. |
| **2. Buscar contenido nuevo** | Trae publicaciones de X y las guarda. No publica nada. |
| **3. Probar sin publicar** | Te enseña qué publicaría y te deja ver la imagen. No publica nada. |
| **4. Publicar en Now Football** | Publica de verdad. |

Los botones **2** y **4** también corren solos (cada 4 y cada 2 horas).
Los botones **1** y **3** son para cuando tú quieras revisar algo.

## Instalación

Sigue la guía paso a paso que te pasó Claude en el chat. Son unos 30 minutos
y es todo de clics.

Si prefieres el resumen: necesitas crear tres cosas gratis (una cuenta de
GitHub, una de twitterapi.io y una app de desarrollador de Facebook), subir
esta carpeta a un repositorio privado, y guardar tres claves en
**Settings → Secrets and variables → Actions**:

- `TWITTERAPI_KEY`
- `FB_PAGE_ID`
- `FB_PAGE_TOKEN`

Tu logo va en `assets/logo.png` (PNG con fondo transparente).

## Costo

GitHub y Facebook son gratis. twitterapi.io cuesta alrededor de **$1.10 USD
al mes** con las tres cuentas actuales. Cada cuenta de X que agregues suma
unos $0.36 al mes.

## Si quieres cambiar algo

Abre el archivo `bot/config.py` desde GitHub (puedes editarlo ahí mismo con
el lapicito). Lo que más se toca:

- `ACCOUNTS` — las cuentas de X que sigue
- `HASHTAGS` — los hashtags de todos los posts
- `MIN_RETWEETS` — qué tan exigente es con la calidad
- `MATURITY_HOURS` — cuántas horas espera antes de juzgar una publicación
- `BLUR_BACKDROP` — pon `False` si prefieres fondo liso en vez de desenfocado

El horario está en `.github/workflows/4-publicar.yml`. Ojo: GitHub usa hora
UTC, y Mazatlán es UTC−7, así que a la hora local súmale 7.

## Derechos de autor

Estás republicando imágenes de terceros en una página comercial. La NFL es
muy agresiva con los avisos de DMCA y un par de strikes pueden costarte la
página. El crédito a la cuenta original ya va en todos los posts; déjalo.
Si te llega un aviso, quita ese post de inmediato.

La solución de fondo es que el bot tome los *datos* y dibuje la tarjeta con
tu propio diseño, en vez de reusar la imagen ajena. Es el siguiente paso
natural de este proyecto.
