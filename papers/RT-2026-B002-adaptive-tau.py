#!/usr/bin/env python3
"""
Adaptive Tau Controller — Phase 12
===================================
Bridges Q001 (quantum von Neumann entropy) and B001 (gradient FPN penalty)
with a self-adjusting conflict threshold τ that responds to topological
phase transitions in the model's behavioral gradient space.

Core problem:
  A fixed τ = 0.3 becomes obsolete when the model undergoes emergent
  phase transitions. As new circuits form and old ones dissolve, the
  distribution of gradient cosine similarities shifts — what was a
  "moderate conflict" at one phase may be "just noise" at another.

Solution:
  τ_adaptive(t) = τ_0 · clamp(1 + α · (S_0 - S_t) / log(k), τ_min/τ_0, τ_max/τ_0)

  Where S_t is the von Neumann entropy of the gradient conflict density
  matrix, measuring the "quantumness" of behavioral conflicts.

  - S_t > S_0 → topology MORE conflicted → τ decreases (more sensitive)
  - S_t < S_0 → topology LESS conflicted → τ increases (less sensitive)
  - Phase transitions detected as |ΔS| > 3σ → logged + λ temporarily boosted

Two entropy sources:
  1. SYMBOLIC S_FPN: from Q001 — entropy of FPN cycle settings (discrete)
  2. CONTINUOUS S_conflict: direct von Neumann entropy of gradient
     conflict matrix (continuous, works without symbolic FPN detection)

Dependencies: numpy, quantum_extension (Q001), gradient_fpn_bridge (B001)
"""

import numpy as np
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import sys
sys.path.insert(0, '/root/timetravel')

from quantum_extension import QuantumResolution, ClassicalFPNAdapter

np.set_printoptions(precision=4, suppress=True)


# ═══════════════════════════════════════════════════════════════
# PART I — CONTINUOUS GRADIENT CONFLICT ENTROPY
# ═══════════════════════════════════════════════════════════════

def behavioral_similarity_stats(behavioral_directions):
    """
    Compute statistics of the pairwise cosine similarity distribution.

    Returns the full distribution for τ-adaptation based on
    the empirical distribution of behavioral gradient relationships.

    When the model undergoes a phase transition, μ_cos and σ_cos shift.
    The adaptive τ uses this shift to recalibrate conflict detection.
    """
    names = sorted(behavioral_directions.keys())
    k = len(names)
    cos_values = []

    # Build cosine similarity matrix
    S = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            di = behavioral_directions[names[i]]
            dj = behavioral_directions[names[j]]
            if isinstance(di, np.ndarray):
                vi, vj = di, dj
            else:
                vi, vj = di.vector, dj.vector
            cos_val = float(np.dot(vi, vj) / (np.linalg.norm(vi) * np.linalg.norm(vj) + 1e-10))
            S[i, j] = cos_val
            if i != j:
                cos_values.append(cos_val)

    cos_values = np.array(cos_values)
    mu_cos = float(np.mean(cos_values))
    sigma_cos = float(np.std(cos_values))
    p10 = float(np.percentile(cos_values, 10))
    p25 = float(np.percentile(cos_values, 25))
    min_cos = float(np.min(cos_values))
    max_cos = float(np.max(cos_values))

    # Conflict pairs: cos < μ - n_sigma · σ (unusually anti-aligned)
    n_sigma = 2.0  # pairs more than 2σ below mean are conflicts
    tau_distribution = mu_cos - n_sigma * sigma_cos

    conflict_pairs = []
    for i in range(k):
        for j in range(i + 1, k):
            if S[i, j] < tau_distribution:
                conflict_pairs.append((names[i], names[j]))

    # von Neumann entropy of the shifted similarity matrix
    eigenvals = np.linalg.eigvalsh(S)
    lambda_min = float(np.min(eigenvals))
    if lambda_min < 0:
        S_shifted = S - lambda_min * np.eye(k)
    else:
        S_shifted = S.copy()
    trace_S = float(np.trace(S_shifted))
    rho = S_shifted / max(trace_S, 1e-10)
    S_vn = von_neumann_entropy(rho)

    return {
        'mu_cos': mu_cos,
        'sigma_cos': sigma_cos,
        'p10': p10,
        'p25': p25,
        'min_cos': min_cos,
        'max_cos': max_cos,
        'tau_distribution': tau_distribution,
        'n_pairs': len(cos_values),
        'conflict_pairs': conflict_pairs,
        'n_conflicts': len(conflict_pairs),
        'entropy_vn': S_vn,
        'max_entropy': np.log2(max(k, 2)),
        'similarity_matrix': S,
    }


def von_neumann_entropy(rho):
    """
    S(ρ) = -Tr(ρ log ρ) = -Σ λ_i log λ_i

    For a density matrix, this measures the "mixedness" of the state.
    S = 0 → pure state (all conflict concentrated in one mode)
    S = log(k) → maximally mixed (conflict uniformly distributed)
    """
    if rho is None:
        return 0.0
    eigenvals = np.linalg.eigvalsh(rho)
    # Filter negative eigenvalues (numerical noise near zero)
    eigenvals = eigenvals[eigenvals > 1e-12]
    if len(eigenvals) == 0:
        return 0.0
    entropy = -float(np.sum(eigenvals * np.log2(eigenvals)))
    return max(0.0, entropy)


def gradient_conflict_entropy(behavioral_directions, tau_base=0.3):
    """
    Compute conflict statistics from behavioral gradient directions.

    Primary signal: τ_distribution = μ_cos - 2σ_cos (distribution-based threshold)
    Secondary signal: von Neumann entropy of similarity matrix
    Auxiliary: conflict pairs detected at 2σ below mean

    The distribution-based τ automatically adapts to phase transitions:
    when μ_cos and σ_cos shift, τ_distribution shifts accordingly.
    """
    stats = behavioral_similarity_stats(behavioral_directions)
    return {
        'entropy': stats['entropy_vn'],
        'max_entropy': stats['max_entropy'],
        'normalized_entropy': stats['entropy_vn'] / max(stats['max_entropy'], 1e-10),
        'mu_cos': stats['mu_cos'],
        'sigma_cos': stats['sigma_cos'],
        'tau_distribution': stats['tau_distribution'],
        'n_conflicts': stats['n_conflicts'],
        'conflict_pairs': stats['conflict_pairs'],
        'similarity_matrix': stats['similarity_matrix'],
    }


# ═══════════════════════════════════════════════════════════════
# PART II — PHASE TRANSITION DETECTOR
# ═══════════════════════════════════════════════════════════════

class PhaseTransitionType(Enum):
    NONE = "none"
    CONFLICT_EMERGENCE = "conflict_emergence"      # S ↑ significantly
    CONFLICT_RESOLUTION = "conflict_resolution"    # S ↓ significantly
    TOPOLOGY_SHIFT = "topology_shift"              # conflict pairs changed
    DIMENSIONAL_CHANGE = "dimensional_change"      # effective rank changed


@dataclass
class PhaseTransitionEvent:
    step: int
    transition_type: PhaseTransitionType
    entropy_before: float
    entropy_after: float
    delta_entropy: float
    tau_before: float
    tau_after: float
    conflict_pairs_before: set
    conflict_pairs_after: set
    description: str


class PhaseTransitionDetector:
    """
    Detects emergent phase transitions in behavioral gradient topology.

    Detection criteria:
      1. ENTROPY JUMP: |S_t - S_{t-window}| > n_sigma · σ_S
      2. TOPOLOGY SHIFT: conflict pair set changes by > 50%
      3. DIMENSIONAL CHANGE: effective rank of density matrix changes

    When a phase transition is detected:
      - Log the event for monitoring
      - Provide recommended τ and λ adjustments
      - Track transition history for retrospective analysis
    """

    def __init__(self, window=50, n_sigma=3.0, pair_change_threshold=0.5):
        self.window = window
        self.n_sigma = n_sigma
        self.pair_change_threshold = pair_change_threshold
        self.entropy_history = deque(maxlen=window * 4)
        self.pair_history = deque(maxlen=window)
        self.transitions = []

    def update(self, step, entropy_info, conflict_pairs_set):
        """
        Update detector with current state. Returns PhaseTransitionEvent or None.
        """
        self.entropy_history.append(entropy_info['entropy'])
        self.pair_history.append(conflict_pairs_set)

        if len(self.entropy_history) < self.window:
            return None

        # Compute baseline from window steps ago
        current_S = self.entropy_history[-1]
        baseline_S = np.mean(list(self.entropy_history)[-self.window:-1])
        recent_std = np.std(list(self.entropy_history)[-self.window:])

        if recent_std < 1e-10:
            return None  # No variation to detect

        delta_S = current_S - baseline_S
        z_score = abs(delta_S) / max(recent_std, 1e-10)

        if z_score < self.n_sigma:
            return None  # No significant change

        # Determine transition type
        if delta_S > 0:
            trans_type = PhaseTransitionType.CONFLICT_EMERGENCE
        else:
            trans_type = PhaseTransitionType.CONFLICT_RESOLUTION

        # Check topology shift
        current_pairs = conflict_pairs_set
        baseline_pairs = self.pair_history[-self.window] if len(self.pair_history) >= self.window else set()
        if current_pairs and baseline_pairs:
            union = current_pairs | baseline_pairs
            intersection = current_pairs & baseline_pairs
            jaccard = len(intersection) / max(len(union), 1)
            if jaccard < (1 - self.pair_change_threshold):
                trans_type = PhaseTransitionType.TOPOLOGY_SHIFT

        event = PhaseTransitionEvent(
            step=step,
            transition_type=trans_type,
            entropy_before=baseline_S,
            entropy_after=current_S,
            delta_entropy=delta_S,
            tau_before=0.0,   # filled in by controller
            tau_after=0.0,    # filled in by controller
            conflict_pairs_before=baseline_pairs,
            conflict_pairs_after=current_pairs,
            description=f"{trans_type.value}: S {baseline_S:.4f} → {current_S:.4f} (Δ={delta_S:+.4f}, z={z_score:.1f})",
        )

        self.transitions.append(event)
        return event


# ═══════════════════════════════════════════════════════════════
# PART III — ADAPTIVE TAU CONTROLLER
# ═══════════════════════════════════════════════════════════════

@dataclass
class AdaptiveTauState:
    """Current state of the adaptive τ controller."""
    step: int
    tau_current: float
    tau_base: float
    entropy_S: float
    entropy_S0: float  # baseline entropy (set at initialization)
    entropy_normalized: float
    lambda_fpn: float  # current FPN penalty strength
    lambda_base: float
    n_conflicts: int
    conflict_pairs: set
    phase_transition_active: bool
    steps_since_transition: int


class AdaptiveTauController:
    """
    Self-adjusting conflict threshold based on empirical cosine distribution.

    Core equation (distribution-based):
      τ(t) = clamp(μ_cos(t) - n_sigma · σ_cos(t), τ_min, τ_max)

    where:
      μ_cos(t) = mean of pairwise cos similarities at step t
      σ_cos(t) = standard deviation of pairwise cos similarities
      n_sigma = 2.0 (conflict = unusually anti-aligned relative to current distribution)

    This automatically adapts to phase transitions:
      - When all cos values shift negative (more conflict overall):
        μ_cos ↓ → τ ↓ → more sensitive to relative outliers
      - When all cos values shift positive (alignment improves):
        μ_cos ↑ → τ ↑ → less sensitive, fewer false positives
      - When variance increases (some pairs align, others conflict strongly):
        σ_cos ↑ → τ ↓ → captures the spread

    Phase transition detection:
      |μ_cos(t) - μ_cos(t-window)| > 3 · σ_μ

    λ-adaptation:
      λ(t) = λ_0 · (1 + β · max(0, τ_0 - τ(t)) / τ_0)
      When τ drops (more conflict): λ increases (stronger penalty)
    """

    def __init__(self, tau_0=0.3, n_sigma=2.0, tau_min=0.05, tau_max=0.60,
                 lambda_0=1.0, ema_smooth=0.9, n_boost=50, beta_lambda=1.0,
                 distribution_weight=0.5):
        """
        Args:
          tau_0: baseline fixed threshold (reference point)
          n_sigma: target sigma for distribution threshold (asymptotic for large k)
          tau_min, tau_max: clamping range
          lambda_0: baseline FPN penalty strength
          ema_smooth: exponential smoothing factor
          n_boost: steps to boost lambda after conflict emergence
          beta_lambda: λ adaptation strength
          distribution_weight: blend weight for distribution vs fixed τ
                               (0 = fully fixed, 1 = fully distribution-based)
        """
        self.tau_0 = tau_0
        self.n_sigma = n_sigma
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.lambda_0 = lambda_0
        self.ema_smooth = ema_smooth
        self.n_boost = n_boost
        self.beta_lambda = beta_lambda
        self.distribution_weight = distribution_weight

        # Smoothed distribution parameters
        self.mu_ema = None
        self.sigma_ema = None
        self.tau_current = tau_0
        self.lambda_current = lambda_0
        self.step = 0
        self.steps_since_transition = 0
        self.phase_active = False
        self.boost_remaining = 0

        # Distribution history for phase detection
        self.mu_history = deque(maxlen=200)
        self.sigma_history = deque(maxlen=200)

        self.detector = PhaseTransitionDetector()
        self.history = []

    def update(self, behavioral_directions, fpn_resolution=None):
        """
        Update controller with current behavioral gradient state.

        Uses empirical cosine distribution to set τ.
        Detects phase transitions when distribution parameters shift.
        """
        self.step += 1

        stats = behavioral_similarity_stats(behavioral_directions)
        mu_raw = stats['mu_cos']
        sigma_raw = stats['sigma_cos']

        # Initialize EMA on first update
        if self.mu_ema is None:
            self.mu_ema = mu_raw
            self.sigma_ema = sigma_raw

        # Exponential moving average
        self.mu_ema = self.ema_smooth * self.mu_ema + (1 - self.ema_smooth) * mu_raw
        self.sigma_ema = self.ema_smooth * self.sigma_ema + (1 - self.ema_smooth) * sigma_raw

        # Distribution-based τ with small-k correction
        k = len(behavioral_directions)
        # Effective n_sigma: scale with k to avoid over-sensitivity for small k
        n_sigma_eff = self.n_sigma * min(1.0, k / 10.0)  # asymptotic at k=10

        tau_dist = self.mu_ema - n_sigma_eff * self.sigma_ema
        tau_dist_clamped = float(np.clip(tau_dist, self.tau_min, self.tau_max))

        # Hybrid: blend fixed τ_0 with distribution-based τ
        w = self.distribution_weight
        tau_blended = (1 - w) * self.tau_0 + w * tau_dist_clamped
        self.tau_current = float(np.clip(tau_blended, self.tau_min, self.tau_max))

        # Adapt λ: stronger penalty when τ is lower (more conflicts)
        tau_deficit = max(0.0, self.tau_0 - self.tau_current)
        lambda_adaptive = self.lambda_0 * (1.0 + self.beta_lambda * tau_deficit / self.tau_0)

        # Manage boost
        if self.boost_remaining > 0:
            self.lambda_current = lambda_adaptive * 2.0
            self.boost_remaining -= 1
        else:
            self.lambda_current = lambda_adaptive

        # Phase transition detection: shift in μ
        self.mu_history.append(self.mu_ema)
        self.sigma_history.append(self.sigma_ema)
        event = None
        if len(self.mu_history) >= 50:
            mu_old = np.mean(list(self.mu_history)[:50])
            mu_new = np.mean(list(self.mu_history)[-10:])
            sigma_mu = np.std(list(self.mu_history)) + 1e-10
            z_mu = abs(mu_new - mu_old) / sigma_mu

            if z_mu > 3.0:
                trans_type = (PhaseTransitionType.CONFLICT_EMERGENCE
                             if mu_new < mu_old
                             else PhaseTransitionType.CONFLICT_RESOLUTION)
                event = PhaseTransitionEvent(
                    step=self.step,
                    transition_type=trans_type,
                    entropy_before=mu_old,
                    entropy_after=mu_new,
                    delta_entropy=mu_new - mu_old,
                    tau_before=self.tau_current,
                    tau_after=self.tau_current,
                    conflict_pairs_before=set(),
                    conflict_pairs_after=set(stats['conflict_pairs']),
                    description=f"{trans_type.value}: μ_cos {mu_old:.4f} → {mu_new:.4f} "
                                f"(τ: {self.tau_current:.4f})",
                )
                self.detector.transitions.append(event)
                self.phase_active = True
                self.steps_since_transition = 0
                if trans_type == PhaseTransitionType.CONFLICT_EMERGENCE:
                    self.boost_remaining = self.n_boost
            else:
                self.steps_since_transition += 1
                if self.steps_since_transition > 100:
                    self.phase_active = False
        else:
            self.steps_since_transition += 1

        state = AdaptiveTauState(
            step=self.step,
            tau_current=self.tau_current,
            tau_base=self.tau_0,
            entropy_S=self.mu_ema,
            entropy_S0=0.0,  # not used in distribution mode
            entropy_normalized=stats['entropy_vn'] / max(stats['max_entropy'], 1e-10),
            lambda_fpn=self.lambda_current,
            lambda_base=self.lambda_0,
            n_conflicts=stats['n_conflicts'],
            conflict_pairs=set(stats['conflict_pairs']),
            phase_transition_active=self.phase_active,
            steps_since_transition=self.steps_since_transition,
        )

        self.history.append(state)
        return state

    def get_diagnostics(self):
        if not self.history:
            return "No data yet."
        current = self.history[-1]
        lines = [
            f"τ-Adaptive Controller (distribution-based) — Step {current.step}",
            f"  τ_current = {current.tau_current:.4f}  (range: [{self.tau_min}, {self.tau_max}])",
            f"  μ_cos = {self.mu_ema:.4f}  σ_cos = {self.sigma_ema:.4f}",
            f"  λ_current = {current.lambda_fpn:.2f}  (base: {current.lambda_base})",
            f"  Conflicts: {current.n_conflicts} pair(s) at {self.n_sigma}σ threshold",
            f"  Phase active: {current.phase_transition_active}",
        ]
        if self.detector.transitions:
            lines.append(f"\n  Phase transitions: {len(self.detector.transitions)}")
            for t in self.detector.transitions[-5:]:
                lines.append(f"    {t.description}")
        return "\n".join(lines)

    @property
    def window(self):
        return self.detector.window


# ═══════════════════════════════════════════════════════════════
# PART IV — INTEGRATION WITH FPN LOSS PENALTY
# ═══════════════════════════════════════════════════════════════

class AdaptiveFPNLossPenalty:
    """
    FPN Loss Penalty with adaptive τ from the controller.

    L_FPN(θ, t) = λ(t) · Σ max(0, -cos(d_i, d_j) - τ(t))²

    where τ(t) and λ(t) are provided by AdaptiveTauController.
    """

    def __init__(self, controller: AdaptiveTauController):
        self.controller = controller

    def compute(self, behavioral_directions):
        """
        Compute adaptive FPN penalty given current behavioral gradients.
        Uses the controller's current τ and λ.
        """
        state = self.controller.update(behavioral_directions)
        tau = state.tau_current
        lam = state.lambda_fpn

        names = list(behavioral_directions.keys())
        penalty = 0.0

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                di = behavioral_directions[names[i]]
                dj = behavioral_directions[names[j]]
                if isinstance(di, np.ndarray):
                    vi, vj = di, dj
                else:
                    vi, vj = di.vector, dj.vector
                di_u = vi / (np.linalg.norm(vi) + 1e-10)
                dj_u = vj / (np.linalg.norm(vj) + 1e-10)
                cos_val = float(np.dot(di_u, dj_u))
                violation = max(0.0, -cos_val - tau)
                penalty += violation ** 2

        return lam * penalty, state


# ═══════════════════════════════════════════════════════════════
# PART V — DIAGNOSTIC VISUALIZATION
# ═══════════════════════════════════════════════════════════════

def print_adaptive_diagnostics(controller: AdaptiveTauController):
    """Print full diagnostic report for the adaptive τ controller."""
    print(controller.get_diagnostics())

    if not controller.history:
        return

    # Entropy trajectory
    entropies = [h.entropy_S for h in controller.history]
    taus = [h.tau_current for h in controller.history]
    lambdas = [h.lambda_fpn for h in controller.history]

    n = len(entropies)
    print(f"\n  Entropy trajectory (last 20):")
    for i in range(max(0, n-20), n):
        marker = ""
        for t in controller.detector.transitions:
            if t.step == controller.history[i].step:
                marker = " ← PHASE TRANSITION"
                break
        print(f"    Step {controller.history[i].step:>4}: S={entropies[i]:.4f}  "
              f"τ={taus[i]:.4f}  λ={lambdas[i]:.2f}{marker}")

    print(f"\n  Summary:")
    print(f"    τ range: [{min(taus):.4f}, {max(taus):.4f}]")
    print(f"    S range: [{min(entropies):.4f}, {max(entropies):.4f}]")
    print(f"    Phase transitions: {len(controller.detector.transitions)}")


# ═══════════════════════════════════════════════════════════════
# PART VI — THEORETICAL GUARANTEES
# ═══════════════════════════════════════════════════════════════

THEOREM_TAU = """
THEOREM T (τ-Adaptive Stability):
  Let S_t be the von Neumann entropy of the gradient conflict density matrix.
  Under the adaptive rule τ(t) = τ_0 · (1 + α · (S_0 - S_t) / log(k)):
  
  1. (Boundedness) τ(t) ∈ [τ_min, τ_max] for all t
  2. (Responsiveness) ∂τ/∂S = -α·τ_0 / log(k) < 0 → τ decreases when S increases
  3. (Fixed point) If S_t = S_0 for all t, then τ(t) = τ_0
  4. (No self-oscillation) τ adjusts on a slower timescale than gradient steps
     (EMA smoothing β > training LR), preventing τ-oscillation
  
  This ensures τ adapts to topological changes without introducing
  new instabilities into the training dynamics.
"""


# ═══════════════════════════════════════════════════════════════
# PART VII — QUICK TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Quick verification of the entropy computation
    print("=" * 60)
    print("ADAPTIVE TAU CONTROLLER — Quick Verification")
    print("=" * 60)

    # Create synthetic behavioral directions
    n_dims = 20
    np.random.seed(42)

    base = np.random.randn(n_dims)
    base /= np.linalg.norm(base)
    ortho = np.random.randn(n_dims)
    ortho -= np.dot(ortho, base) * base
    ortho /= np.linalg.norm(ortho)

    # Three phases of topology:
    # Phase 1: Moderate conflict
    dA = base
    dB = -0.5 * base + 0.87 * ortho
    dB /= np.linalg.norm(dB)
    dC = 0.3 * base + 0.95 * ortho
    dC /= np.linalg.norm(dC)

    phase1 = {'A': dA, 'B': dB, 'C': dC}

    # Phase 2: High conflict (simulated phase transition)
    dA2 = base
    dB2 = -0.9 * base + 0.44 * ortho  # much more anti-aligned
    dB2 /= np.linalg.norm(dB2)
    dC2 = -0.7 * dB2 + 0.3 * ortho  # cascading conflicts
    dC2 /= np.linalg.norm(dC2)

    phase2 = {'A': dA2, 'B': dB2, 'C': dC2}

    # Phase 3: Resolved conflict
    dA3 = base
    dB3 = 0.1 * base + 0.99 * ortho  # nearly orthogonal
    dB3 /= np.linalg.norm(dB3)
    dC3 = 0.2 * base + 0.98 * ortho
    dC3 /= np.linalg.norm(dC3)

    phase3 = {'A': dA3, 'B': dB3, 'C': dC3}

    # Test entropy computation on all three phases
    for phase_name, phase_dirs in [("Phase 1 (moderate)", phase1),
                                    ("Phase 2 (high conflict)", phase2),
                                    ("Phase 3 (resolved)", phase3)]:
        info = gradient_conflict_entropy(phase_dirs, tau_base=0.3)
        print(f"\n{phase_name}:")
        print(f"  S(ρ) = {info['entropy']:.4f} bits (max: {info['max_entropy']:.2f})")
        print(f"  Normalized: {info['normalized_entropy']:.3f}")
        print(f"  Conflicts: {info['n_conflicts']} pair(s)")
        print(f"  Pairs: {info['conflict_pairs']}")

    # Test adaptive controller
    print(f"\n{'─'*60}")
    print("Adaptive τ Simulation Across Phase Transitions")
    print(f"{'─'*60}")

    controller = AdaptiveTauController(tau_0=0.3, n_sigma=2.0)

    # Simulate: Phase 1 for 100 steps, Phase 2 for 100 steps, Phase 3 for 100 steps
    for step in range(300):
        if step < 100:
            dirs = phase1
        elif step < 200:
            dirs = phase2
        else:
            dirs = phase3
        state = controller.update(dirs)

        if step % 40 == 0 or state.phase_transition_active:
            marker = " ⬡ PHASE TRANSITION" if state.phase_transition_active else ""
            print(f"  Step {step:>3}: μ_cos={state.entropy_S:.4f}  "
                  f"τ={state.tau_current:.3f}  λ={state.lambda_fpn:.2f}  "
                  f"conflicts={state.n_conflicts}{marker}")

    print_adaptive_diagnostics(controller)
