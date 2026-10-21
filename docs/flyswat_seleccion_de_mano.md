# Selección de mano en FlySwat

## Decisión recomendada

Para la primera versión de FlySwat, usar **una sola mano activa**, aunque MediaPipe detecte dos manos en pantalla.

- Mantener la regla de juego simple: una pinza cerca de la mosca realiza la captura.
- Evitar ambigüedades sobre qué mano controla el juego.
- Reducir falsas capturas y parpadeos.
- Conservar buen rendimiento, especialmente en dispositivos móviles.
- Dejar la arquitectura preparada para admitir dos manos en el futuro.

## Configuración de MediaPipe

Configurar el `HandLandmarker` con:

```ts
numHands: 2
```

Aunque el juego use una única mano activa, pedir dos permite decidir explícitamente cuál utilizar.

Con `numHands: 1`, MediaPipe devuelve solo una mano, pero no ofrece una regla estable ni un identificador persistente: si hay dos manos, puede alternar entre ellas entre frames.

## Cómo elegir la mano activa

Regla sugerida, en orden de prioridad:

1. Si solo una mano está haciendo pinza, esa es la mano activa.
2. Si ambas manos hacen pinza, elegir la cuyo punto de pinza esté más cerca de la mosca.
3. Si ninguna hace pinza, mantener la última mano activa mientras siga detectada.
4. Si no hay mano previa activa, elegir la mano más cercana a la mosca.
5. Aplicar una pequeña histéresis temporal para evitar cambios bruscos entre manos.

## Implementación propuesta

```ts
function selectActiveHand(
  hands: HandState[],
  flyPosition: Vec2,
  previousHand?: HandState,
): HandState | null {
  const pinching = hands.filter(hand => hand.isPinching);

  if (pinching.length === 1) {
    return pinching[0];
  }

  if (pinching.length > 1) {
    return minBy(
      pinching,
      hand => distance(hand.pinchPoint, flyPosition),
    );
  }

  if (previousHand && hands.includes(previousHand)) {
    return previousHand;
  }

  return hands.length
    ? minBy(
        hands,
        hand => distance(hand.pinchPoint, flyPosition),
      )
    : null;
}
```

## Cambio en los tipos

La salida de visión puede representarse como un conjunto de manos:

```ts
export interface HandsState {
  hands: HandState[];
}
```

El juego puede seguir recibiendo una única mano activa:

```ts
game.step({
  action: policy.act(state, activeHand, dt),
  hand: activeHand,
  dt,
});
```

Así, la lógica de física, huida y captura no cambia al pasar de una mano a dos.

## Etiqueta de mano

MediaPipe devuelve una etiqueta de lateralidad, `Left` o `Right`, para cada mano detectada, junto con una puntuación de confianza.

- No debe usarse como identificador estable entre frames.
- Puede invertirse según si la imagen de la webcam está espejada o no.
- Para la lógica del juego, es más robusto usar la posición del punto de pinza y la distancia a la mosca.
- La etiqueta puede mostrarse en la interfaz, pero no debería determinar por sí sola qué mano controla el juego.

## Modos futuros

Si más adelante se quiere usar ambas manos, pueden añadirse modos opcionales:

| Modo | Interacción |
|---|---|
| Base | Una mano activa y una mosca |
| Dos moscas | Una mano por mosca |
| Red | Ambas pinzas cerradas cerca de la mosca |
| Cooperativo | Dos jugadores, una mano cada uno |

## Conclusión

Para el MVP: detectar hasta dos manos, pero seleccionar automáticamente **una mano activa** mediante pinza y proximidad a la mosca. Esto mantiene el juego sencillo, estable y fácil de explicar, sin cerrar la puerta a modos con dos manos.
