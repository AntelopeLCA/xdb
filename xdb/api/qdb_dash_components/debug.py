"""
Debug Page Component

Displays the current user selection data as JSON for debugging purposes.
"""

from dash import html
import dash_bootstrap_components as dbc
import json


def create_debug_page():
    """
    Create the debug page for viewing selection data.

    Returns:
        A Dash component containing the debug view
    """
    return html.Div([
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
                html.H3('Debug: User Selection', className='mb-3')
            ])
        ]),

        # Selection data display
        dbc.Card([
            dbc.CardHeader(html.H5('Current Selection Data')),
            dbc.CardBody([
                html.Pre(
                    id='debug-selection-json',
                    style={
                        'backgroundColor': '#f8f9fa',
                        'padding': '15px',
                        'borderRadius': '5px',
                        'fontSize': '14px',
                        'fontFamily': 'monospace',
                        'overflow': 'auto',
                        'maxHeight': '600px'
                    }
                )
            ])
        ], className='mb-3'),

        # Additional info
        dbc.Card([
            dbc.CardHeader(html.H5('Selection Summary')),
            dbc.CardBody([
                html.Div(id='debug-summary')
            ])
        ])
    ])
