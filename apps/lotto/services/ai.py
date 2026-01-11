from __future__ import annotations

import math
import random
from typing import List, Dict, Any

from ..models import Draw


def predict_next_draw_probabilities(
    draws: List[Draw],
    seed: str | None = None,
    max_samples: int = 400,
    hidden_size: int = 24,
    epochs: int = 25,
    learning_rate: float = 0.15,
    max_number: int = 50,
    main_count: int = 7,
) -> Dict[str, Any]:
    ordered = sorted(draws, key=lambda d: d.date)
    if len(ordered) < 2:
        return {
            'probabilities': [{'number': i, 'probability': 0.0} for i in range(1, max_number + 1)],
            'top_numbers': [],
            'meta': {
                'draws_used': len(ordered),
                'samples': 0,
                'hidden_size': hidden_size,
                'epochs': 0,
                'learning_rate': learning_rate,
            },
        }

    inputs, targets = _build_training_pairs(ordered, max_samples=max_samples, max_number=max_number)
    rng = random.Random(seed or 42)
    model = _train_mlp(
        inputs,
        targets,
        hidden_size=hidden_size,
        epochs=epochs,
        learning_rate=learning_rate,
        rng=rng,
        max_number=max_number,
    )

    last_draw = ordered[-1]
    x = _multi_hot(last_draw.numbers, max_number=max_number)
    probs = _forward(model, x)

    probability_list = [
        {'number': idx + 1, 'probability': prob}
        for idx, prob in enumerate(probs)
    ]
    top_numbers = [
        item['number']
        for item in sorted(probability_list, key=lambda i: i['probability'], reverse=True)[:main_count]
    ]

    return {
        'probabilities': probability_list,
        'top_numbers': top_numbers,
        'meta': {
            'draws_used': len(ordered),
            'samples': len(inputs),
            'hidden_size': hidden_size,
            'epochs': epochs,
            'learning_rate': learning_rate,
        },
    }


def _build_training_pairs(
    draws: List[Draw],
    max_samples: int,
    max_number: int = 50,
) -> tuple[list[list[float]], list[list[float]]]:
    pairs = []
    for current, nxt in zip(draws[:-1], draws[1:]):
        pairs.append((_multi_hot(current.numbers, max_number=max_number), _multi_hot(nxt.numbers, max_number=max_number)))
    if max_samples and len(pairs) > max_samples:
        pairs = pairs[-max_samples:]
    inputs = [p[0] for p in pairs]
    targets = [p[1] for p in pairs]
    return inputs, targets


def _multi_hot(numbers: List[int], max_number: int = 50) -> list[float]:
    vec = [0.0] * max_number
    for n in numbers:
        if 1 <= n <= max_number:
            vec[n - 1] = 1.0
    return vec


def _train_mlp(
    inputs: list[list[float]],
    targets: list[list[float]],
    hidden_size: int,
    epochs: int,
    learning_rate: float,
    rng: random.Random,
    max_number: int = 50,
) -> dict:
    input_size = max_number
    output_size = max_number

    w1 = [[rng.uniform(-0.08, 0.08) for _ in range(hidden_size)] for _ in range(input_size)]
    b1 = [0.0 for _ in range(hidden_size)]
    w2 = [[rng.uniform(-0.08, 0.08) for _ in range(output_size)] for _ in range(hidden_size)]
    b2 = [0.0 for _ in range(output_size)]

    for _ in range(max(epochs, 1)):
        for x, y in zip(inputs, targets):
            z1 = [b1[j] + _dot_col(x, w1, j) for j in range(hidden_size)]
            h = [max(0.0, z) for z in z1]
            z2 = [b2[k] + _dot_row(h, w2, k) for k in range(output_size)]
            yhat = [1.0 / (1.0 + math.exp(-z)) for z in z2]

            delta2 = [yhat[k] - y[k] for k in range(output_size)]
            delta1 = []
            for j in range(hidden_size):
                back = sum(delta2[k] * w2[j][k] for k in range(output_size))
                delta1.append(back if z1[j] > 0.0 else 0.0)

            for j in range(hidden_size):
                for k in range(output_size):
                    w2[j][k] -= learning_rate * delta2[k] * h[j]
            for k in range(output_size):
                b2[k] -= learning_rate * delta2[k]

            for i in range(input_size):
                if x[i] == 0.0:
                    continue
                for j in range(hidden_size):
                    w1[i][j] -= learning_rate * delta1[j] * x[i]
            for j in range(hidden_size):
                b1[j] -= learning_rate * delta1[j]

    return {'w1': w1, 'b1': b1, 'w2': w2, 'b2': b2}


def _forward(model: dict, x: list[float]) -> list[float]:
    w1 = model['w1']
    b1 = model['b1']
    w2 = model['w2']
    b2 = model['b2']
    hidden_size = len(b1)
    output_size = len(b2)

    z1 = [b1[j] + _dot_col(x, w1, j) for j in range(hidden_size)]
    h = [max(0.0, z) for z in z1]
    z2 = [b2[k] + _dot_row(h, w2, k) for k in range(output_size)]
    return [1.0 / (1.0 + math.exp(-z)) for z in z2]


def _dot_col(x: list[float], matrix: list[list[float]], col: int) -> float:
    return sum(x[i] * matrix[i][col] for i in range(len(x)))


def _dot_row(x: list[float], matrix: list[list[float]], col: int) -> float:
    return sum(x[j] * matrix[j][col] for j in range(len(x)))
