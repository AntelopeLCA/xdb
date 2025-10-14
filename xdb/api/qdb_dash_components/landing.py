"""
Landing/Search Page Component

Main search interface with search bar and results in three columns.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from .doco import landing_text


def create_landing_page():
    """
    Create the landing page with search functionality.

    Returns:
        A Dash component containing the search interface
    """
    return html.Div([
        # Search bar section
        dbc.Row([
            dbc.Col([
                landing_text(),
                dbc.Row([
                    dbc.Col([
                        html.Div(id='current-search-queries'),
                    ], width=11),
                    dbc.Col([
                    dbc.Button(
                        'Clear Search',
                        id='clear-search-button',
                        color='secondary',
                        size='sm',
                        outline=True,
                        className='mb-3'),
                    ])
                ]),
                dbc.InputGroup([
                    dbc.Input(
                        id='search-input',
                        placeholder='Enter search term...',
                        type='text',
                        className='form-control-lg'
                    ),
                    dbc.Button(
                        'Search',
                        id='search-button',
                        color='primary',
                        className='btn-lg'
                    )
                ], className='mb-4')
            ], width=12)
        ]),

        # Search results section - three columns
        dbc.Row([
            # Flowables column
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.H5('Flowables', className='mb-3')
                        ]),
                    dbc.Col([
                        dbc.Button(
                            'Add All',
                            id='add-all-flowables-button',
                            color='success',
                            size='sm',
                            outline=True
                        )
                        ], style={'text-align': 'right'})
                    ]),
                html.Div(id='flowables-results', children=[
                    html.P('No results yet. Enter a search term above.',
                           className='text-muted', style={'fontStyle': 'italic'})
                ])
            ], width=4, style={'borderRight': '1px solid #dee2e6', 'paddingRight': '20px'}),

            # Contexts column
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.H5('Contexts', className='mb-3')
                        ]),
                    dbc.Col([
                        dbc.Button(
                            'Add All',
                            id='add-all-contexts-button',
                            color='success',
                            size='sm',
                            outline=True
                        )
                        ], style={'text-align': 'right'})
                    ]),
                html.Div(id='contexts-results', children=[
                    html.P('No results yet. Enter a search term above.',
                           className='text-muted', style={'fontStyle': 'italic'})
                ])
            ], width=4, style={'borderRight': '1px solid #dee2e6', 'paddingRight': '20px'}),

            # Quantities column
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.H5('Quantities', className='mb-3')
                        ]),
                    dbc.Col([
                        dbc.Button(
                            'Add All',
                            id='add-all-quantities-button',
                            color='success',
                            size='sm',
                            outline=True
                        )
                        ], style={'text-align': 'right'})
                    ]),
                html.Div(id='quantities-results', children=[
                    html.P('No results yet. Enter a search term above.',
                           className='text-muted', style={'fontStyle': 'italic'})
                ])
            ], width=4)
        ], className='mt-4')
    ])


def create_result_item(item_id, item_name, item_type, is_selected=False):
    """
    Create a single search result item with view/add/remove buttons.

    Args:
        item_id: Unique identifier for the item
        item_name: Display name of the item
        item_type: Type of item ('flowable', 'context', or 'quantity')
        is_selected: Whether this item is in the current selection

    Returns:
        A Dash component for the result item
    """
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                # Item name (left)
                html.Div([
                    html.Strong(item_name),
                    html.Br(),
                    html.Small(f'ID: {item_id}', className='text-muted')
                ], style={'flex': '1'}),

                # Action buttons (right)
                html.Div([
                    dbc.Button(
                        html.I(className='bi bi-eye'),
                        id={'type': 'view-button', 'index': f'{item_type}:{item_id}'},
                        color='info',
                        size='sm',
                        outline=True,
                        href=f'/qdb.dash/detail/{item_type}/{item_id}',
                        title='View details',
                        style={'marginRight': '5px'}
                    ),
                    dbc.Button(
                        html.I(className='bi bi-plus-circle' if not is_selected else 'bi bi-dash-circle'),
                        id={'type': 'add-button', 'index': f'{item_type}:{item_id}'},
                        color='success' if not is_selected else 'primary',
                        size='sm',
                        outline=not is_selected,
                        # disabled=is_selected,
                        title='Add to selection' if not is_selected else 'Already in selection',
                        style={'marginRight': '5px'}
                    ),
                    dbc.Button(
                        html.I(className='bi bi-x-circle'),
                        id={'type': 'remove-button', 'index': f'{item_type}:{item_id}'},
                        color='danger',
                        size='sm',
                        outline=True,
                        title='Remove from results'
                    )
                ], style={'display': 'flex', 'gap': '5px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'})
        ], style={'padding': '10px'})
    ], className='mb-2', id='_result_%s_%s' % (item_type, item_id))
