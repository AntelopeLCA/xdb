"""
Debug Page Callbacks

Callbacks for displaying debug information.
"""

from dash import Input, Output, State, html
import json


def register(app):
    """Register debug page callbacks."""

    @app.callback(
        Output('debug-selection-json', 'children'),
        Input('user-selection', 'data')
    )
    def display_selection_json(selection_data):
        """
        Display the user selection data as formatted JSON.

        Args:
            selection_data: Current user selection

        Returns:
            Formatted JSON string
        """
        if not selection_data:
            return "No selection data available"

        return json.dumps(selection_data, indent=2)

    @app.callback(
        Output('debug-summary', 'children'),
        Input('user-selection', 'data')
    )
    def display_selection_summary(selection_data):
        """
        Display a summary of the selection data.

        Args:
            selection_data: Current user selection

        Returns:
            HTML summary
        """
        if not selection_data:
            return html.P("No selection data available")

        flowables_count = len(selection_data.get('flowables', []))
        contexts_count = len(selection_data.get('contexts', []))
        quantities_count = len(selection_data.get('quantities', []))
        total = flowables_count + contexts_count + quantities_count

        return html.Div([
            html.P([
                html.Strong('Total items: '),
                html.Span(str(total))
            ]),
            html.Ul([
                html.Li(f'Flowables: {flowables_count}'),
                html.Li(f'Contexts: {contexts_count}'),
                html.Li(f'Quantities: {quantities_count}')
            ])
        ])
