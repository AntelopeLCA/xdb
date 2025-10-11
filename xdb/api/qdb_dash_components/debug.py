"""
Debug Page Component

Displays the current user selection data as JSON for debugging purposes.
"""

from dash import html
import dash_bootstrap_components as dbc
import json

from ..runtime import cat
import logging


QDB_LCIA = [('lcia.openlca.2.7.5', '2e5cd15d-d539-3141-a950-56d75df9d579'),]


def _pre_load():
    logging.warning('Pre-loading ReCipe Specs')
    orgs = set()
    items = []
    for org in cat.pre_load:
        list([l for l in cat.query(org).lcia_methods()])
        orgs.add(org)
        items.append(html.P(f"Pre-load {org}"))
    for org, meth in QDB_LCIA:
        if org in orgs:
            continue
        cat.pre_load_query(org)
        e = cat.query(org).get(meth)
        items.append(html.P(f"Methodology {e}"))
        for i in e['ImpactCategories']:
            o = cat.query(org).get(i)
            items.append(html.P(f"Method {o}", style={'margin-bottom': 0}))
    logging.warning('Done')
    return html.Div(items)


def create_debug_page():
    """
    Create the debug page for viewing selection data.

    Returns:
        A Dash component containing the debug view
    """

    return html.Div([
        # Header
        _pre_load(),
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
