"""
Banner Component

Top banner with logos, auth status, selection summary, and action buttons.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_banner():
    """
    Create the top banner component with logos, status, and buttons.

    Returns:
        A Dash component containing the banner layout
    """
    return dbc.Navbar(
        dbc.Container([
            # Left logo
            html.Img(
                src='/qdb.dash/assets/qdb.png',
                height='50px',
                style={'marginRight': '20px'}
            ),

            # Center section: Auth status and selection summary
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(id='auth-status-display', children=[
                            html.Span('Auth: ', style={'fontWeight': 'bold'}),
                            html.Span('Not authenticated', id='auth-status-text',
                                     style={'color': '#999'})
                        ], style={'marginBottom': '5px'}),
                        html.Div(id='selection-summary', children=[
                            html.Span('Selection: ', style={'fontWeight': 'bold'}),
                            html.Span('0 items', id='selection-count')
                        ])
                    ], style={'fontSize': '14px'})
                ], width='auto')
            ], className='mx-auto'),

            # Action buttons
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        'Analyze',
                        id='analyze-button',
                        color='primary',
                        size='sm',
                        href='/qdb.dash/analyze',
                        style={'marginRight': '10px'}
                    ),
                    dbc.Button(
                        'Debug',
                        id='debug-button',
                        color='info',
                        size='sm',
                        outline=True,
                        href='/qdb.dash/debug',
                        style={'marginRight': '10px'}
                    ),
                    dbc.Button(
                        'Clear',
                        id='clear-selection-button',
                        color='secondary',
                        size='sm',
                        outline=True
                    )
                ], width='auto')
            ]),

            # Right logo
            html.Img(
                src='/qdb.dash/assets/wordmark-Antelope-fixed.png',
                height='50px',
                style={'marginLeft': '20px'}
            )
        ], fluid=True, style={'display': 'flex', 'alignItems': 'center'}),
        color='light',
        dark=False,
        className='mb-4',
        style={'padding': '10px 20px'}
    )
