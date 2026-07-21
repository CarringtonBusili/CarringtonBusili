"""Shared chart palette and Plotly layout defaults for the dashboard."""
import plotly.graph_objects as go
import plotly.io as pio

CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
DIVERGING = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]

STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"

_template = go.layout.Template()
_template.layout = go.Layout(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=TEXT_SECONDARY, size=13),
    title=dict(font=dict(color=TEXT_PRIMARY, size=16)),
    xaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, tickfont=dict(color=TEXT_MUTED)),
    yaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, tickfont=dict(color=TEXT_MUTED)),
    legend=dict(font=dict(color=TEXT_SECONDARY)),
    colorway=CATEGORICAL,
    margin=dict(t=50, r=20, b=40, l=50),
)
pio.templates["edgars_mfp"] = _template
pio.templates.default = "edgars_mfp"


def apply(fig: go.Figure) -> go.Figure:
    fig.update_layout(template="edgars_mfp")
    return fig
