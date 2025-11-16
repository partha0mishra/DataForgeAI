"""Chart builder for creating visualizations."""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class ChartBuilder:
    """
    Chart builder for creating Plotly visualizations.

    Provides:
    - Line charts, bar charts, pie charts
    - Scatter plots, heatmaps, area charts
    - Tables and metrics
    - Custom styling and theming
    - Interactive features

    Example:
        builder = ChartBuilder()

        # Create line chart
        fig = builder.create_line_chart(
            data=df,
            x="date",
            y="revenue",
            title="Monthly Revenue",
            color="region"
        )

        # Create bar chart
        fig = builder.create_bar_chart(
            data=df,
            x="product",
            y="sales",
            title="Sales by Product"
        )

        # Get chart JSON
        chart_json = builder.to_json(fig)
    """

    def __init__(self, theme: str = "plotly"):
        """
        Initialize chart builder.

        Args:
            theme: Plotly theme (plotly, plotly_white, plotly_dark, etc.)
        """
        self.theme = theme
        self.logger = logger

        self.logger.info("Chart builder initialized", theme=theme)

    def create_line_chart(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: Optional[str] = None,
        line_dash: Optional[str] = None,
        markers: bool = False,
        **kwargs,
    ) -> go.Figure:
        """
        Create line chart.

        Args:
            data: DataFrame with data
            x: Column for x-axis
            y: Column for y-axis
            title: Chart title
            color: Column for color grouping
            line_dash: Column for line style grouping
            markers: Show markers on line
            **kwargs: Additional plotly express parameters

        Returns:
            Plotly figure
        """
        fig = px.line(
            data,
            x=x,
            y=y,
            title=title,
            color=color,
            line_dash=line_dash,
            markers=markers,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Line chart created", title=title)

        return fig

    def create_bar_chart(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: Optional[str] = None,
        orientation: str = "v",
        barmode: str = "group",
        **kwargs,
    ) -> go.Figure:
        """
        Create bar chart.

        Args:
            data: DataFrame with data
            x: Column for x-axis
            y: Column for y-axis
            title: Chart title
            color: Column for color grouping
            orientation: 'v' for vertical, 'h' for horizontal
            barmode: 'group', 'stack', 'relative'
            **kwargs: Additional parameters

        Returns:
            Plotly figure
        """
        fig = px.bar(
            data,
            x=x,
            y=y,
            title=title,
            color=color,
            orientation=orientation,
            barmode=barmode,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Bar chart created", title=title)

        return fig

    def create_pie_chart(
        self,
        data: pd.DataFrame,
        values: str,
        names: str,
        title: str = "",
        hole: float = 0.0,
        **kwargs,
    ) -> go.Figure:
        """
        Create pie chart or donut chart.

        Args:
            data: DataFrame with data
            values: Column for values
            names: Column for labels
            title: Chart title
            hole: Size of hole (0 for pie, >0 for donut)
            **kwargs: Additional parameters

        Returns:
            Plotly figure
        """
        fig = px.pie(
            data,
            values=values,
            names=names,
            title=title,
            hole=hole,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Pie chart created", title=title)

        return fig

    def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: Optional[str] = None,
        size: Optional[str] = None,
        hover_data: Optional[List[str]] = None,
        trendline: Optional[str] = None,
        **kwargs,
    ) -> go.Figure:
        """
        Create scatter plot.

        Args:
            data: DataFrame with data
            x: Column for x-axis
            y: Column for y-axis
            title: Chart title
            color: Column for color
            size: Column for marker size
            hover_data: Columns to show on hover
            trendline: 'ols', 'lowess', etc.
            **kwargs: Additional parameters

        Returns:
            Plotly figure
        """
        fig = px.scatter(
            data,
            x=x,
            y=y,
            title=title,
            color=color,
            size=size,
            hover_data=hover_data,
            trendline=trendline,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Scatter plot created", title=title)

        return fig

    def create_heatmap(
        self,
        data: pd.DataFrame,
        x: Optional[str] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
        title: str = "",
        color_continuous_scale: str = "Viridis",
        **kwargs,
    ) -> go.Figure:
        """
        Create heatmap.

        Args:
            data: DataFrame or 2D array
            x: Column for x-axis (if using long-form data)
            y: Column for y-axis (if using long-form data)
            z: Column for values (if using long-form data)
            title: Chart title
            color_continuous_scale: Color scale
            **kwargs: Additional parameters

        Returns:
            Plotly figure
        """
        if x and y and z:
            # Long-form data
            pivot_data = data.pivot(index=y, columns=x, values=z)
        else:
            # Already in matrix form
            pivot_data = data

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns.tolist(),
                y=pivot_data.index.tolist(),
                colorscale=color_continuous_scale,
            )
        )

        fig.update_layout(
            title=title,
            template=self.theme,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Heatmap created", title=title)

        return fig

    def create_area_chart(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: Optional[str] = None,
        **kwargs,
    ) -> go.Figure:
        """Create area chart."""
        fig = px.area(
            data,
            x=x,
            y=y,
            title=title,
            color=color,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Area chart created", title=title)

        return fig

    def create_table(
        self,
        data: pd.DataFrame,
        title: str = "",
        columns: Optional[List[str]] = None,
        max_rows: Optional[int] = None,
    ) -> go.Figure:
        """
        Create data table.

        Args:
            data: DataFrame with data
            title: Table title
            columns: Columns to display (all if None)
            max_rows: Maximum rows to display

        Returns:
            Plotly figure
        """
        if columns:
            display_data = data[columns]
        else:
            display_data = data

        if max_rows:
            display_data = display_data.head(max_rows)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=list(display_data.columns),
                        fill_color="paleturquoise",
                        align="left",
                    ),
                    cells=dict(
                        values=[display_data[col] for col in display_data.columns],
                        fill_color="lavender",
                        align="left",
                    ),
                )
            ]
        )

        fig.update_layout(
            title=title,
            template=self.theme,
        )

        self.logger.debug("Table created", title=title, rows=len(display_data))

        return fig

    def create_metric(
        self,
        value: float,
        title: str = "",
        delta: Optional[float] = None,
        delta_label: str = "",
        format: str = ",.2f",
    ) -> go.Figure:
        """
        Create metric card.

        Args:
            value: Metric value
            title: Metric title
            delta: Change from previous
            delta_label: Label for delta
            format: Number format

        Returns:
            Plotly figure
        """
        formatted_value = f"{value:{format}}"

        # Create indicator
        fig = go.Figure()

        indicator_args = {
            "mode": "number",
            "value": value,
            "title": {"text": title},
            "number": {"valueformat": format},
        }

        if delta is not None:
            indicator_args["mode"] = "number+delta"
            indicator_args["delta"] = {
                "reference": value - delta,
                "valueformat": format,
                "relative": False,
            }

        fig.add_trace(go.Indicator(**indicator_args))

        fig.update_layout(
            template=self.theme,
            height=200,
        )

        self.logger.debug("Metric created", title=title, value=value)

        return fig

    def create_gauge(
        self,
        value: float,
        title: str = "",
        min_value: float = 0,
        max_value: float = 100,
        threshold: Optional[float] = None,
    ) -> go.Figure:
        """
        Create gauge chart.

        Args:
            value: Current value
            title: Gauge title
            min_value: Minimum value
            max_value: Maximum value
            threshold: Threshold value

        Returns:
            Plotly figure
        """
        fig = go.Figure()

        gauge_args = {
            "axis": {"range": [min_value, max_value]},
            "bar": {"color": "darkblue"},
        }

        if threshold:
            gauge_args["threshold"] = {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": threshold,
            }

        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": title},
                gauge=gauge_args,
            )
        )

        fig.update_layout(
            template=self.theme,
            height=300,
        )

        self.logger.debug("Gauge created", title=title, value=value)

        return fig

    def create_funnel(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        **kwargs,
    ) -> go.Figure:
        """Create funnel chart."""
        fig = px.funnel(
            data,
            x=x,
            y=y,
            title=title,
            template=self.theme,
            **kwargs,
        )

        self._apply_default_layout(fig)

        self.logger.debug("Funnel created", title=title)

        return fig

    def _apply_default_layout(self, fig: go.Figure) -> None:
        """Apply default layout settings."""
        fig.update_layout(
            hovermode="closest",
            showlegend=True,
            height=400,
        )

    def to_json(self, fig: go.Figure) -> str:
        """Convert figure to JSON."""
        return fig.to_json()

    def to_html(self, fig: go.Figure, include_plotlyjs: str = "cdn") -> str:
        """
        Convert figure to HTML.

        Args:
            fig: Plotly figure
            include_plotlyjs: 'cdn', True, False

        Returns:
            HTML string
        """
        return fig.to_html(include_plotlyjs=include_plotlyjs)

    def apply_theme(self, fig: go.Figure, theme: str) -> go.Figure:
        """Apply theme to figure."""
        fig.update_layout(template=theme)
        return fig

    def add_annotation(
        self,
        fig: go.Figure,
        x: Any,
        y: Any,
        text: str,
        **kwargs,
    ) -> go.Figure:
        """Add annotation to figure."""
        fig.add_annotation(
            x=x,
            y=y,
            text=text,
            showarrow=True,
            **kwargs,
        )
        return fig
