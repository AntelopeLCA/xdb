"""
QDB Dash Application

This module creates a Plotly Dash application for the Quantity Database (QDB).
The app is designed to be mounted as WSGI middleware within FastAPI.

To integrate with FastAPI in xdb/api/qdb.py:
    from a2wsgi import WSGIMiddleware
    from xdb.api.qdb_dash import create_dash_app

    dash_app = create_dash_app()
    app.mount("/qdb.dash", WSGIMiddleware(dash_app.server))
"""

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc


def create_dash_app(requests_pathname_prefix="/qdb.dash/"):
    """
    Create and configure the Dash application.

    Args:
        requests_pathname_prefix: The URL prefix where the app will be mounted

    Returns:
        A configured Dash application instance
    """
    app = dash.Dash(
        __name__,
        title="qdb | Antelope",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"
        ],
        requests_pathname_prefix=requests_pathname_prefix,
        suppress_callback_exceptions=True
    )

    # Import components
    from api.qdb_dash_components.banner import create_banner

    # Main app layout with URL routing
    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='user-selection', storage_type='session', data={
            'flowables': [],
            'contexts': [],
            'quantities': []
        }),
        dcc.Store(id='search-results-cache', storage_type='session', data={
            'flowables': [],
            'contexts': [],
            'quantities': []
        }),
        dcc.Store(id='auth-info', data={}),  # Will be populated from FastAPI
        create_banner(),
        html.Div(id='page-content', style={'padding': '20px'})
    ])

    # Register callbacks
    register_callbacks(app)

    return app


def register_callbacks(app):
    """Register all callbacks for the application."""

    # Page routing callback
    @app.callback(
        Output('page-content', 'children'),
        Input('url', 'pathname')
    )
    def display_page(pathname):
        """Route to appropriate page based on URL."""
        from api.qdb_dash_components.landing import create_landing_page
        from api.qdb_dash_components.detail import create_detail_page
        from api.qdb_dash_components.analyze import create_analyze_page
        from api.qdb_dash_components.debug import create_debug_page

        if pathname and pathname.startswith('/qdb.dash/detail/'):
            # Extract entity type and ID from URL
            parts = pathname.split('/')
            if len(parts) >= 4:
                entity_type = parts[3]
                entity_id = parts[4] if len(parts) > 4 else None
                return create_detail_page(entity_type, entity_id)
            return create_detail_page()
        elif pathname and '/debug' in pathname:
            return create_debug_page()
        elif pathname and '/analyze' in pathname:
            return create_analyze_page()
        else:
            # Default to landing page
            return create_landing_page()

    # Import component callbacks
    from api.qdb_dash_components import banner_callbacks
    from api.qdb_dash_components import landing_callbacks
    from api.qdb_dash_components import detail_callbacks
    from api.qdb_dash_components import analyze_callbacks
    from api.qdb_dash_components import debug_callbacks

    banner_callbacks.register(app)
    landing_callbacks.register(app)
    detail_callbacks.register(app)
    analyze_callbacks.register(app)
    debug_callbacks.register(app)


# Create the app instance
dash_app = create_dash_app()
server = dash_app.server


if __name__ == '__main__':
    dash_app.run_server(debug=True, port=8051)
