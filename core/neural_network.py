"""
Neural Network — A real, working feedforward neural network built with numpy.
Supports live state broadcasting for visualization.
"""
import numpy as np
import logging
import threading
import time
import json
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("nexusmind.neural_network")


class NeuralNetwork:
    """
    Feedforward neural network with backpropagation.
    Supports configurable layers, activation functions, and live state export.
    """

    def __init__(self, layer_sizes: List[int], learning_rate: float = 0.1, activation: str = "sigmoid"):
        """
        Args:
            layer_sizes: e.g. [2, 8, 4, 1] → 2 inputs, two hidden layers (8, 4), 1 output
            learning_rate: step size for gradient descent
            activation: 'sigmoid' or 'relu'
        """
        self.layer_sizes = layer_sizes
        self.learning_rate = learning_rate
        self.activation_name = activation
        self.num_layers = len(layer_sizes)

        # Xavier initialization
        self.weights: List[np.ndarray] = []
        self.biases: List[np.ndarray] = []
        for i in range(self.num_layers - 1):
            scale = np.sqrt(2.0 / (layer_sizes[i] + layer_sizes[i + 1]))
            w = np.random.randn(layer_sizes[i], layer_sizes[i + 1]) * scale
            b = np.zeros((1, layer_sizes[i + 1]))
            self.weights.append(w)
            self.biases.append(b)

        # Cache for activations (used in visualization)
        self.activations: List[np.ndarray] = []
        self.z_values: List[np.ndarray] = []

        # Training state
        self.epoch = 0
        self.loss_history: List[float] = []
        self.accuracy_history: List[float] = []
        self.is_training = False
        self._stop_training = False
        self._training_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        logger.info(f"Created neural network: {layer_sizes}, lr={learning_rate}, activation={activation}")

    # ─── Activation Functions ────────────────────────────
    def _activate(self, z: np.ndarray) -> np.ndarray:
        if self.activation_name == "relu":
            return np.maximum(0, z)
        # sigmoid (default)
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    def _activate_derivative(self, a: np.ndarray) -> np.ndarray:
        if self.activation_name == "relu":
            return (a > 0).astype(float)
        # sigmoid derivative
        return a * (1 - a)

    # ─── Forward Pass ────────────────────────────────────
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Forward propagation. Caches activations for backprop and visualization."""
        self.activations = [X.copy()]
        self.z_values = []

        current = X
        for i in range(self.num_layers - 1):
            z = current @ self.weights[i] + self.biases[i]
            self.z_values.append(z)
            current = self._activate(z)
            self.activations.append(current.copy())

        return current

    # ─── Backward Pass ───────────────────────────────────
    def backward(self, X: np.ndarray, y: np.ndarray, output: np.ndarray):
        """Backpropagation with gradient descent."""
        m = X.shape[0]

        # Output layer error
        delta = (output - y) * self._activate_derivative(output)

        # Backpropagate through layers
        for i in range(self.num_layers - 2, -1, -1):
            dw = (self.activations[i].T @ delta) / m
            db = np.sum(delta, axis=0, keepdims=True) / m

            if i > 0:
                delta = (delta @ self.weights[i].T) * self._activate_derivative(self.activations[i])

            self.weights[i] -= self.learning_rate * dw
            self.biases[i] -= self.learning_rate * db

    # ─── Training ────────────────────────────────────────
    def train_step(self, X: np.ndarray, y: np.ndarray) -> float:
        """Single training step. Returns loss."""
        output = self.forward(X)
        self.backward(X, y, output)

        # MSE loss
        loss = float(np.mean((y - output) ** 2))
        return loss

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 1000,
              callback=None, batch_size: int = None):
        """
        Train the network.
        Args:
            callback: optional function(epoch, loss, accuracy) called each epoch
            batch_size: if set, use mini-batch gradient descent
        """
        self.is_training = True
        self._stop_training = False
        self.loss_history = []
        self.accuracy_history = []

        for ep in range(epochs):
            if self._stop_training:
                break

            if batch_size and batch_size < X.shape[0]:
                # Mini-batch
                indices = np.random.permutation(X.shape[0])
                total_loss = 0
                n_batches = 0
                for start in range(0, X.shape[0], batch_size):
                    end = min(start + batch_size, X.shape[0])
                    batch_idx = indices[start:end]
                    loss = self.train_step(X[batch_idx], y[batch_idx])
                    total_loss += loss
                    n_batches += 1
                loss = total_loss / n_batches
            else:
                loss = self.train_step(X, y)

            self.epoch = ep + 1
            self.loss_history.append(loss)

            # Calculate accuracy
            predictions = self.predict(X)
            if y.shape[1] == 1:
                # Binary classification
                acc = float(np.mean((predictions > 0.5).astype(int) == y.astype(int)))
            else:
                # Multi-class
                acc = float(np.mean(np.argmax(predictions, axis=1) == np.argmax(y, axis=1)))
            self.accuracy_history.append(acc)

            if callback:
                callback(self.epoch, loss, acc)

            # Small sleep every 10 epochs for thread responsiveness
            if ep % 10 == 0:
                time.sleep(0.001)

        self.is_training = False
        logger.info(f"Training complete. Final loss: {loss:.6f}, accuracy: {acc:.4f}")

    def train_async(self, X: np.ndarray, y: np.ndarray, epochs: int = 1000,
                    callback=None, batch_size: int = None):
        """Start training in a background thread."""
        self._training_thread = threading.Thread(
            target=self.train, args=(X, y, epochs, callback, batch_size), daemon=True
        )
        self._training_thread.start()

    def stop_training(self):
        """Stop training gracefully."""
        self._stop_training = True
        if self._training_thread:
            self._training_thread.join(timeout=5)

    # ─── Prediction ──────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Run forward pass and return predictions."""
        return self.forward(X)

    # ─── State Export (for visualization) ────────────────
    def get_state(self) -> Dict[str, Any]:
        """
        Export the full network state for live visualization.
        Returns layer sizes, weights, biases, and current activations.
        """
        with self._lock:
            state = {
                "layer_sizes": self.layer_sizes,
                "num_layers": self.num_layers,
                "activation": self.activation_name,
                "learning_rate": self.learning_rate,
                "epoch": self.epoch,
                "is_training": self.is_training,
                "loss": self.loss_history[-1] if self.loss_history else None,
                "accuracy": self.accuracy_history[-1] if self.accuracy_history else None,
                "loss_history": self.loss_history[-100:],  # Last 100 points
                "accuracy_history": self.accuracy_history[-100:],
                "weights": [],
                "biases": [],
                "activations": [],
            }

            for w in self.weights:
                state["weights"].append(w.tolist())
            for b in self.biases:
                state["biases"].append(b[0].tolist())
            for a in self.activations:
                # Average activation per neuron for visualization
                if a.ndim > 1:
                    state["activations"].append(np.mean(a, axis=0).tolist())
                else:
                    state["activations"].append(a.tolist())

            return state

    def reset(self):
        """Re-initialize all weights and clear training history."""
        self.stop_training()
        self.__init__(self.layer_sizes, self.learning_rate, self.activation_name)


# ─── Demo Datasets ───────────────────────────────────────
def get_demo_dataset(name: str = "xor") -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """
    Returns (X, y, recommended_layers) for demo datasets.
    """
    if name == "xor":
        X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float64)
        y = np.array([[0], [1], [1], [0]], dtype=np.float64)
        return X, y, [2, 8, 4, 1]

    elif name == "circles":
        np.random.seed(42)
        n = 200
        r1 = np.random.randn(n // 2) * 0.3 + 1
        r2 = np.random.randn(n // 2) * 0.3 + 3
        theta = np.random.rand(n // 2) * 2 * np.pi
        theta2 = np.random.rand(n // 2) * 2 * np.pi
        X = np.vstack([
            np.column_stack([r1 * np.cos(theta), r1 * np.sin(theta)]),
            np.column_stack([r2 * np.cos(theta2), r2 * np.sin(theta2)])
        ])
        y = np.vstack([np.zeros((n // 2, 1)), np.ones((n // 2, 1))])
        return X, y, [2, 16, 8, 1]

    elif name == "spiral":
        np.random.seed(42)
        n = 150
        t = np.linspace(0, 4 * np.pi, n)
        X = np.vstack([
            np.column_stack([t * np.cos(t) * 0.1, t * np.sin(t) * 0.1]),
            np.column_stack([t * np.cos(t + np.pi) * 0.1, t * np.sin(t + np.pi) * 0.1])
        ])
        X += np.random.randn(*X.shape) * 0.1
        y = np.vstack([np.zeros((n, 1)), np.ones((n, 1))])
        return X, y, [2, 32, 16, 8, 1]

    elif name == "digits":
        # Simple 3x3 digit patterns (0-3)
        patterns = {
            0: [1,1,1, 1,0,1, 1,0,1, 1,0,1, 1,1,1],
            1: [0,1,0, 1,1,0, 0,1,0, 0,1,0, 1,1,1],
            2: [1,1,1, 0,0,1, 1,1,1, 1,0,0, 1,1,1],
            3: [1,1,1, 0,0,1, 1,1,1, 0,0,1, 1,1,1],
        }
        X_list, y_list = [], []
        for digit, pattern in patterns.items():
            for _ in range(25):  # 25 noisy copies each
                noisy = np.array(pattern, dtype=np.float64) + np.random.randn(15) * 0.1
                X_list.append(noisy)
                one_hot = [0, 0, 0, 0]
                one_hot[digit] = 1
                y_list.append(one_hot)
        X = np.array(X_list)
        y = np.array(y_list)
        return X, y, [15, 32, 16, 4]

    else:
        raise ValueError(f"Unknown dataset: {name}")


# ─── Global Instance ─────────────────────────────────────
_network: Optional[NeuralNetwork] = None


def get_network() -> Optional[NeuralNetwork]:
    return _network


def create_network(layer_sizes: List[int], learning_rate: float = 0.1,
                   activation: str = "sigmoid") -> NeuralNetwork:
    global _network
    if _network and _network.is_training:
        _network.stop_training()
    _network = NeuralNetwork(layer_sizes, learning_rate, activation)
    return _network
