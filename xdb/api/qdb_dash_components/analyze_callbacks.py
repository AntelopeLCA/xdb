"""
Analyze Page Callbacks

Callbacks for the analysis functionality.
"""

from dash import Input, Output, State, html, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from .analyze import create_results_table, create_results_chart, analyze_selection, create_results_table_simple
from ..runtime import cat

lcia = cat.lcia_engine


def register(app):
    """Register analyze page callbacks."""

    @app.callback(
        Output('analyze-selection-summary', 'children'),
        Input('user-selection', 'data')
    )
    def display_selection_summary(selection_data):
        """
        Display a list of selected items with remove buttons.

        Args:
            selection_data: Current user selection

        Returns:
            HTML list of selected items with remove buttons
        """
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

        # Create list items for each selected entity
        items = []

        # Add flowables
        fb_items = [dbc.ListGroupItem([
                    html.Div([
                        html.Span('Flowable: ', style={'fontWeight': 'bold'}),
                        html.Span(item_id, style={'flex': '1'}),
                        dbc.Button(
                            html.I(className='bi bi-x-circle'),
                            id={'type': 'analyze-remove-button', 'index': f'flowable:{item_id}'},
                            color='danger',
                            size='sm',
                            outline=True,
                            title='Remove from selection'
                        )
                    ], style={'display': 'flex',
                              'alignItems': 'center',
                              'justifyContent': 'space-between',
                              'gap': '10px'})
            ]) for item_id in flowables]

        # Add contexts
        cx_items = [dbc.ListGroupItem([
                    html.Div([
                        html.Span('Context: ', style={'fontWeight': 'bold'}),
                        html.Span(item_id, style={'flex': '1'}),
                        dbc.Button(
                            html.I(className='bi bi-x-circle'),
                            id={'type': 'analyze-remove-button', 'index': f'context:{item_id}'},
                            color='danger',
                            size='sm',
                            outline=True,
                            title='Remove from selection'
                        )
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'gap': '10px'})
                ]) for item_id in contexts]

        # Add quantities
        q_items = [dbc.ListGroupItem([
                    html.Div([
                        html.Span('Quantity: ', style={'fontWeight': 'bold'}),
                        html.Span(lcia.get_canonical(item_id).name, style={'flex': '1'}),
                        dbc.Button(
                            html.I(className='bi bi-x-circle'),
                            id={'type': 'analyze-remove-button', 'index': f'quantity:{item_id}'},
                            color='danger',
                            size='sm',
                            outline=True,
                            title='Remove from selection'
                        )
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'gap': '10px'})
                ]) for item_id in quantities]

        return html.Div([
            html.P(f'Total: {total} items selected', className='mb-2', style={'fontWeight': 'bold'}),
            dbc.Row([
                dbc.Col([
                    html.H4("Flowables"),
                    dbc.ListGroup(fb_items) if len(fb_items) > 0 else html.P("none selected")
                ], width=4),
                dbc.Col([
                    html.H4("Contexts"),
                    dbc.ListGroup(cx_items) if len(cx_items) > 0 else html.P("none selected")
                ], width=4),
                dbc.Col([
                    html.H4("Quantities"),
                    dbc.ListGroup(q_items) if len(q_items) > 0 else html.P("none selected")
                ], width=4),
            ])
            ])

    @app.callback(
        Output('user-selection', 'data', allow_duplicate=True),
        Input({'type': 'analyze-remove-button', 'index': ALL}, 'n_clicks'),
        State('user-selection', 'data'),
        prevent_initial_call=True
    )
    def remove_from_selection(n_clicks_list, selection_data):
        """
        Remove an item from the selection when X button is clicked.

        Args:
            n_clicks_list: List of click counts for all remove buttons
            selection_data: Current user selection

        Returns:
            Updated selection data
        """
        from dash import ctx, no_update

        if not ctx.triggered_id:
            return no_update

        # Check if this was an actual click
        triggered_value = ctx.triggered[0]['value']
        if triggered_value is None or triggered_value == 0:
            return no_update

        # Get the clicked button's index
        button_index = ctx.triggered_id['index']
        entity_type, entity_id = button_index.split(':', 1)

        # Create new selection
        new_selection = {
            'flowables': selection_data.get('flowables', []).copy(),
            'contexts': selection_data.get('contexts', []).copy(),
            'quantities': selection_data.get('quantities', []).copy()
        }

        # Remove from appropriate list
        if entity_type == 'flowable' and entity_id in new_selection['flowables']:
            new_selection['flowables'].remove(entity_id)
        elif entity_type == 'context' and entity_id in new_selection['contexts']:
            new_selection['contexts'].remove(entity_id)
        elif entity_type == 'quantity' and entity_id in new_selection['quantities']:
            new_selection['quantities'].remove(entity_id)

        return new_selection

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
            return create_results_table_simple(df)
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
