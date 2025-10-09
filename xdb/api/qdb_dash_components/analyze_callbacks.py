"""
Analyze Page Callbacks

Callbacks for the analysis functionality.
"""

from dash import Input, Output, State, html
import dash_bootstrap_components as dbc
import pandas as pd
from .analyze import create_results_table, create_results_chart, analyze_selection


def register(app):
    """Register analyze page callbacks."""

    @app.callback(
        Output('analyze-selection-summary', 'children'),
        Input('url', 'pathname'),
        State('user-selection', 'data')
    )
    def display_selection_summary(pathname, selection_data):
        """
        Display a summary of the current selection on the analyze page.

        Args:
            pathname: Current URL path
            selection_data: Current user selection

        Returns:
            HTML summary of the selection
        """
        if not pathname or '/analyze' not in pathname:
            return html.P('No selection data.')

        if not selection_data:
            return dbc.Alert(
                'No items selected. Please return to the search page and select items to analyze.',
                color='warning'
            )

        flowables = selection_data.get('flowables', [])
        contexts = selection_data.get('contexts', [])
        quantities = selection_data.get('quantities', [])

        total = len(flowables) + len(contexts) + len(quantities)

        if total == 0:
            return dbc.Alert(
                'No items selected. Please return to the search page and select items to analyze.',
                color='warning'
            )

        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong('Flowables: '),
                    html.Span(f'{len(flowables)} selected')
                ], width=4),
                dbc.Col([
                    html.Strong('Contexts: '),
                    html.Span(f'{len(contexts)} selected')
                ], width=4),
                dbc.Col([
                    html.Strong('Quantities: '),
                    html.Span(f'{len(quantities)} selected')
                ], width=4)
            ]),
            html.Hr(),
            html.P(f'Total: {total} items selected', className='mb-0')
        ])

    @app.callback(
        Output('analysis-results-display', 'children'),
        Input('run-analysis-button', 'n_clicks'),
        State('user-selection', 'data'),
        State('analysis-type-dropdown', 'value'),
        prevent_initial_call=True
    )
    def run_analysis(n_clicks, selection_data, analysis_type):
        """
        Execute the analysis on the selected items.

        Args:
            n_clicks: Number of times run button was clicked
            selection_data: Current user selection
            analysis_type: Type of analysis to perform

        Returns:
            Analysis results display component
        """
        if not selection_data:
            return dbc.Alert('No selection data available.', color='warning')

        # Check if any items are selected
        total = (
            len(selection_data.get('flowables', [])) +
            len(selection_data.get('contexts', [])) +
            len(selection_data.get('quantities', []))
        )

        if total == 0:
            return dbc.Alert(
                'No items selected. Please select items before running analysis.',
                color='warning'
            )

        # Run analysis (STUB call)
        results = analyze_selection(selection_data)

        if not results:
            # Return placeholder content since this is a stub
            return html.Div([
                dbc.Alert(
                    'Analysis complete. Results will be displayed here once backend implementation is connected.',
                    color='info'
                ),
                html.Div([
                    html.H6('Selected Items:'),
                    html.Ul([
                        html.Li(f'Flowables: {", ".join(selection_data.get("flowables", []))}') if selection_data.get('flowables') else None,
                        html.Li(f'Contexts: {", ".join(selection_data.get("contexts", []))}') if selection_data.get('contexts') else None,
                        html.Li(f'Quantities: {", ".join(selection_data.get("quantities", []))}') if selection_data.get('quantities') else None,
                    ])
                ])
            ])

        # Display results based on analysis type
        if analysis_type == 'table':
            # Assume results contains a dataframe
            df = results.get('dataframe')
            return create_results_table(df)
        elif analysis_type == 'chart':
            # Assume results contains chart data
            chart_data = results.get('chart_data')
            return create_results_chart('bar', chart_data)
        else:  # report
            # Display a detailed report
            return html.Div([
                html.H5('Analysis Report'),
                html.P('Detailed report will be displayed here.')
            ])

    @app.callback(
        Output('export-results-button', 'n_clicks'),
        Input('export-results-button', 'n_clicks'),
        State('user-selection', 'data'),
        State('export-format-dropdown', 'value'),
        prevent_initial_call=True
    )
    def export_results(n_clicks, selection_data, export_format):
        """
        Export analysis results to file.

        Args:
            n_clicks: Number of times export button was clicked
            selection_data: Current user selection
            export_format: Format for export (csv, xlsx, json)

        Returns:
            None (triggers download in actual implementation)
        """
        # STUB: This would trigger a download of the analysis results
        # TODO: Implement actual export functionality using dcc.Download
        # For now, this is just a placeholder
        pass
