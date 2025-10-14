"""
Analyze Page Component

Displays analysis results for the user's current selection,
including Pandas tables or charts.
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from .qdb_analyzer import QdbAnalyzer
from ..runtime import cat


# STUB: Replace with actual backend analysis
def analyze_selection(selection_data):
    """
    STUB: Analyze the user's selection and return results.

    Args:
        selection_data: Dictionary with flowables, contexts, quantities lists

    Returns:
        Dictionary with analysis results (dataframes, charts, etc.)
    """
    q_ana = QdbAnalyzer(cat, flowables=selection_data.get('flowables', []),
                        contexts=selection_data.get('contexts', []),
                        quantities=selection_data.get('quantities', []))
    return {'dataframe': q_ana.analyze(),
            'debug': q_ana.debug_for_flowables()}


def debug_selection(selection_data):
    q_ana = QdbAnalyzer(cat, flowables=selection_data.get('flowables', []),
                        contexts=selection_data.get('contexts', []),
                        quantities=selection_data.get('quantities', []))
    return dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    f
                ]),dbc.Col([str(k) for k in cat.lcia_engine.factors_for_flowable(f)])
            ])
            for f in selection_data.get('flowables')
        ])
    ])


def _pre_load():
    items = []

    for org in cat.pre_load:
        for l in cat.query(org).lcia_methods():
            cat.flush_factors(l)
        items.append(html.P(f"Pre-load {org}"))

    return html.Div(items)


def create_analyze_page():
    """
    Create the analyze page for displaying analysis results.

    Returns:
        A Dash component containing the analysis view
    """
    return html.Div([
        dcc.Download(id='download-dataframe'),
        _pre_load(),
        # Header
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    html.I(className='bi bi-arrow-left'),
                    href='/qdb.dash/',
                    color='secondary',
                    size='sm',
                    className='mb-3'
                )
            ], width='auto'),
            dbc.Col([
                html.H3('Analysis Results', className='mb-3')
            ])
        ]),

        # Selection summary
        dbc.Card([
            dbc.CardHeader(html.H5('Current Selection')),
            dbc.CardBody([
                html.Div(id='analyze-selection-summary')
            ])
        ], className='mb-3'),

        # Analysis controls
        dbc.Card([
            dbc.CardHeader(html.H5('Analysis Options')),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label('Analysis Type:', className='mb-2'),
                        dcc.Dropdown(
                            id='analysis-type-dropdown',
                            options=[
                                {'label': 'Summary Table', 'value': 'table'},
                                {'label': 'Chart View', 'value': 'chart'},
                                {'label': 'Detailed Report', 'value': 'report'},
                                {'label': 'Debug', 'value': 'debug'}
                            ],
                            value='table',
                            className='mb-3'
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label('Export Format:', className='mb-2'),
                        dcc.Dropdown(
                            id='export-format-dropdown',
                            options=[
                                {'label': 'CSV', 'value': 'csv'},
                                {'label': 'Excel', 'value': 'xlsx'},
                                {'label': 'JSON', 'value': 'json'}
                            ],
                            value='csv',
                            className='mb-3'
                        )
                    ], width=6)
                ]),
                dbc.Button(
                    'Run Analysis',
                    id='run-analysis-button',
                    color='primary',
                    className='me-2'
                ),
                dbc.Button(
                    'Export Results',
                    id='export-results-button',
                    color='secondary',
                    outline=True
                )
            ])
        ], className='mb-3'),

        # Results display
        dbc.Card([
            dbc.CardHeader(html.H5('Results')),
            dbc.CardBody([
                html.Div(id='analysis-results-display', children=[
                    html.P('Click "Run Analysis" to see results.',
                           className='text-muted', style={'fontStyle': 'italic'})
                ])
            ])
        ])
    ])


def create_results_table_simple(df):
    """
    Create a Dash DataTable from a pandas DataFrame.

    Args:
        df: pandas DataFrame with results

    Returns:
        Dash DataTable component
    """
    if df is None or df.empty:
        return html.P('No data to display.', className='text-muted')

    return dbc.Table.from_dataframe(df[:100].reset_index())


def create_results_table(df):
    """
    Create a Dash DataTable from a pandas DataFrame.

    Args:
        df: pandas DataFrame with results

    Returns:
        Dash DataTable component
    """
    if df is None or df.empty:
        return html.P('No data to display.', className='text-muted')

    return dash_table.DataTable(
        data=df.reset_index().to_dict('records'),
        columns=[{'name': col, 'id': col} for col in df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'minWidth': '100px'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'borderBottom': '2px solid #dee2e6'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        page_size=20,
        sort_action='native',
        filter_action='native'
    )


def create_results_chart(chart_type, data):
    """
    Create a plotly chart from analysis data.

    Args:
        chart_type: Type of chart to create
        data: Data for the chart

    Returns:
        dcc.Graph component
    """
    # STUB: This would create actual charts based on the analysis results
    return dcc.Graph(
        figure={
            'data': [],
            'layout': {
                'title': 'Chart will be displayed here',
                'xaxis': {'title': 'X Axis'},
                'yaxis': {'title': 'Y Axis'}
            }
        }
    )
