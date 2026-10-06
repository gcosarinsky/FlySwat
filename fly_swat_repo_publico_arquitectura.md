# Fly Swat: un repositorio público para mostrar código

## Objetivo real

El propósito principal de este proyecto no es demostrar dominio de *reinforcement learning* (RL) ni aportar una idea de investigación original. Es disponer de un repositorio público, pequeño y bien terminado, que permita ver cómo diseño, implemento, pruebo y documento software.

El código de mis proyectos de investigación no siempre se puede publicar y, cuando es público, puede ser demasiado específico o no estar organizado como me gustaría mostrarlo. Este proyecto funcionaría como una muestra de código complementaria a mi experiencia en imagen, GPU e IA aplicada; no como sustituto de ella.

## Alcance recomendado: juego sin RL

Implementar primero una demo con webcam en la que el jugador intenta atrapar una mosca virtual juntando índice y pulgar:

- MediaPipe proporciona las posiciones de las puntas del índice y el pulgar.
- El punto medio entre ambas define la posición de interacción.
- La distancia entre los dedos permite detectar el gesto de pinza.
- La mosca se mueve con velocidad, inercia, aceleración limitada y rebote en los bordes.
- Si el usuario hace pinza suficientemente cerca de la mosca, se registra una captura.
- Se pueden alternar políticas de movimiento sin cambiar la física ni la lógica de colisión.

No hace falta incluir RL para que este repositorio cumpla su función de muestra de software.

## Políticas intercambiables

El juego puede ofrecer inicialmente dos políticas:

1. **Aleatoria suave:** elige una dirección de aceleración aleatoria y la mantiene durante varios frames. La inercia y el límite de aceleración evitan cambios de trayectoria demasiado bruscos.
2. **Huida heurística:** calcula el punto medio entre índice y pulgar; si la mano está suficientemente cerca, elige la dirección que aleja a la mosca de ese punto. Lejos de la mano, puede mantener la dirección anterior o volver al movimiento aleatorio.

Ambas son políticas *fijas*: no aprenden. La primera es estocástica y la segunda está definida por reglas. Son útiles como modos de juego y, si algún día se añade DQN, como baselines.

La política decide una acción; el motor del juego aplica siempre la misma dinámica:

```text
estado del juego + mano observada
             ↓
        policy.act(...)
             ↓
   acción: dirección de aceleración
             ↓
   GameState.step(action, hand_state, dt)
             ↓
 nuevo estado + eventos (rebote, captura, etc.)
```

## Arquitectura inicial, sin Gymnasium

No implementaría el juego directamente como un entorno Gymnasium si todavía no se va a entrenar un agente. Gymnasium aporta una interfaz estándar para RL, pero añadirlo ahora obligaría a definir observaciones, recompensas y señales de terminación que no son necesarias para una demo basada en reglas.

Separaría cuatro responsabilidades:

```text
src/fly_swat/
├── vision.py       # Webcam, MediaPipe y coordenadas de los dos dedos
├── gestures.py     # Punto de interacción y detección estable de pinza
├── game.py         # Estado, física, bordes, colisiones y puntuación
├── policies.py     # Política aleatoria y política heurística de huida
├── rendering.py    # Cámara, mosca, efectos e interfaz visual
└── app.py          # Bucle principal y conexión entre componentes
```

Es una estructura orientativa, no una obligación: si el proyecto queda más claro con menos módulos, conviene simplificar.

La función central podría tener una interfaz similar a:

```python
next_state, events = game.step(
    action=policy.act(state, hand_state),
    hand_state=hand_state,
    dt=dt,
)
```

`game.step` no debería importar OpenCV, MediaPipe ni Gymnasium. Así se puede probar la lógica del juego sin cámara y reutilizarla más adelante.

## Qué debería mostrar un «repo bonito»

- Un README con una frase que explique el juego, una demo visual corta y pasos de instalación y ejecución.
- Dependencias declaradas y una forma reproducible de arrancar.
- Código legible, con responsabilidades claras y nombres coherentes.
- Tests de lógica que no requieran webcam: detección de pinch, colisiones, rebotes y selección de acciones.
- Configuración breve de parámetros (velocidad, aceleración, radio de captura), sin valores mágicos dispersos.
- Un ejemplo de vídeo o GIF que permita evaluar el proyecto sin instalarlo.
- Opcionalmente, CI que ejecute los tests automáticamente.

La prioridad es que el proyecto sea fácil de inspeccionar y ejecutar. Una implementación pequeña y terminada es preferible a una arquitectura extensa con componentes inacabados.

## Cuándo añadir Gymnasium

Si después se decide entrenar DQN, incorporaría un adaptador separado, por ejemplo `FlyEnv(gymnasium.Env)`, que **reutilice** la física de `game.py`:

```python
class FlyEnv(gym.Env):
    def reset(self, *, seed=None, options=None):
        # Reiniciar GameState y devolver observación e info.
        ...

    def step(self, action):
        # Avanzar GameState y convertir el resultado a
        # observación, reward, terminated, truncated, info.
        ...
```

En ese momento sí habría que definir el espacio de acciones, la observación, la recompensa, la política de la mano durante el entrenamiento y la evaluación. El adaptador serviría para entrenar, pero el juego interactivo seguiría compartiendo el mismo núcleo.

**Regla de diseño:** primero construir el juego; si hay un experimento de RL genuino, envolver el juego en Gymnasium. No meter Gymnasium «por si acaso».

## Cómo decidir si merece la pena añadir RL

Antes de incorporar DQN al CV, compararlo contra las dos políticas iniciales:

- Mosca aleatoria suave.
- Mosca con huida heurística.
- Mosca entrenada con DQN.

Evaluar en trayectorias de mano que no se hayan usado para entrenar y, sobre todo, jugando en vivo. Las trayectorias grabadas no reaccionan a la mosca que está aprendiendo a escapar; por eso superar un replay de unos pocos vídeos no demuestra necesariamente que el agente esquive bien a un jugador real.

Si RL no mejora de manera convincente el comportamiento o la experiencia, se puede dejar como experimento documentado y mantener el repo principal centrado en la demo de visión y software. No conviene afirmar especialización en RL por haber integrado una librería o un modelo.

## Presentación en el CV

Una vez terminado y publicado, incluirlo de forma secundaria, en una sección como *Selected open-source projects* o *Public code*:

> **Fly Swat — real-time computer vision demo** · Python, OpenCV, MediaPipe. Built a webcam-controlled game with pinch detection, interchangeable movement policies, a testable game engine, and a short visual demo. [GitHub]

Si más adelante se entrena y evalúa DQN con resultados claros, se puede actualizar la descripción para mencionar el agente aprendido y su comparación con baselines. Hasta entonces, es más preciso venderlo como **un repositorio de código bien hecho** que como una demostración de experiencia en RL.
