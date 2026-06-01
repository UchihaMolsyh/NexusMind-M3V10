"""
LaTeX to Unicode Math Symbol Converter
Converts mathematical notation from LaTeX format to readable Unicode/ASCII.
"""
import re


def convert_latex_to_unicode(text: str) -> str:
    """
    Convert LaTeX math expressions to readable Unicode symbols.
    Examples:
        \\frac{1}{2} → 1/2
        \\sqrt{x} → √x
        \\pi → π
    """
    if not text:
        return text
    
    # Fractions: \frac{a}{b} → a/b
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)
    
    # Brackets: \left( \right) → ( )
    text = text.replace(r'\left(', '(').replace(r'\right)', ')')
    text = text.replace(r'\left[', '[').replace(r'\right]', ']')
    text = text.replace(r'\left\{', '{').replace(r'\right\}', '}')
    
    # Text blocks: \text{abc} → abc
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    
    # Square root: \sqrt{x} → √x
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√\1', text)
    
    # Greek letters (lowercase)
    greek_lower = {
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
        r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
        r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
        r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
        r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
        r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    }
    
    # Greek letters (uppercase)
    greek_upper = {
        r'\Alpha': 'Α', r'\Beta': 'Β', r'\Gamma': 'Γ', r'\Delta': 'Δ',
        r'\Epsilon': 'Ε', r'\Zeta': 'Ζ', r'\Eta': 'Η', r'\Theta': 'Θ',
        r'\Iota': 'Ι', r'\Kappa': 'Κ', r'\Lambda': 'Λ', r'\Mu': 'Μ',
        r'\Nu': 'Ν', r'\Xi': 'Ξ', r'\Omicron': 'Ο', r'\Pi': 'Π',
        r'\Rho': 'Ρ', r'\Sigma': 'Σ', r'\Tau': 'Τ', r'\Upsilon': 'Υ',
        r'\Phi': 'Φ', r'\Chi': 'Χ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
    }
    
    # Mathematical symbols
    math_symbols = {
        r'\infty': '∞', r'\sum': '∑', r'\prod': '∏', r'\int': '∫',
        r'\approx': '≈', r'\neq': '≠', r'\leq': '≤', r'\geq': '≥',
        r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
        r'\cdot': '·', r'\emptyset': '∅', r'\in': '∈', r'\notin': '∉',
        r'\subset': '⊂', r'\supset': '⊃', r'\subseteq': '⊆', r'\supseteq': '⊇',
        r'\cup': '∪', r'\cap': '∩', r'\exists': '∃', r'\forall': '∀',
        r'\nabla': '∇', r'\partial': '∂', r'\to': '→', r'\rightarrow': '→',
        r'\leftarrow': '←', r'\Rightarrow': '⇒', r'\Leftarrow': '⇐',
        r'\iff': '⇔', r'\therefore': '∴', r'\because': '∵',
    }
    
    # Apply all replacements (longest match first to avoid partial replacements)
    all_replacements = {**greek_lower, **greek_upper, **math_symbols}
    for latex, unicode_char in sorted(all_replacements.items(), key=lambda x: -len(x[0])):
        text = text.replace(latex, unicode_char)
    
    # Handle superscripts: x^2 → x², x^{10} → x¹⁰
    superscripts = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ',
    }
    text = re.sub(r'\^\{([^}]+)\}', lambda m: ''.join(superscripts.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'\^(\d)', lambda m: superscripts.get(m.group(1), m.group(1)), text)
    
    # Handle subscripts: x_1 → x₁, x_{12} → x₁₂
    subscripts = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
        'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ',
        'h': 'ₕ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ',
        'n': 'ₙ', 'p': 'ₚ', 's': 'ₛ', 't': 'ₜ',
    }
    text = re.sub(r'_\{([^}]+)\}', lambda m: ''.join(subscripts.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'_(\d|[a-z])', lambda m: subscripts.get(m.group(1), m.group(1)), text)
    
    return text
