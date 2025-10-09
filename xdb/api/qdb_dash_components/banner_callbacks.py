"""
Banner Callbacks

Callbacks for the banner component: selection summary and clear button.
"""

from dash import Input, Output, State, html


def register(app):
    """Register banner-related callbacks."""

    @app.callback(
        Output('selection-count', 'children'),
        Input('user-selection', 'data')
    )
    def update_selection_count(selection_data):
        """
        Update the selection count display in the banner.

        Args:
            selection_data: Dictionary with flowables, contexts, quantities lists

        Returns:
            Formatted string showing selection count
        """
        if not selection_data:
            return '0 items'

        total = (
            len(selection_data.get('flowables', [])) +
            len(selection_data.get('contexts', [])) +
            len(selection_data.get('quantities', []))
        )

        if total == 0:
            return '0 items'
        elif total == 1:
            return '1 item'
        else:
            # Show breakdown
            parts = []
            if selection_data.get('flowables'):
                parts.append(f"{len(selection_data['flowables'])} flowable(s)")
            if selection_data.get('contexts'):
                parts.append(f"{len(selection_data['contexts'])} context(s)")
            if selection_data.get('quantities'):
                parts.append(f"{len(selection_data['quantities'])} quantity/ies")

            return ' | '.join(parts)

    @app.callback(
        Output('user-selection', 'data', allow_duplicate=True),
        Input('clear-selection-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_selection(n_clicks):
        """
        Clear all items from the user selection.

        Args:
            n_clicks: Number of times the clear button has been clicked

        Returns:
            Empty selection dictionary
        """
        if n_clicks:
            return {
                'flowables': [],
                'contexts': [],
                'quantities': []
            }
        return {
            'flowables': [],
            'contexts': [],
            'quantities': []
        }

    @app.callback(
        Output('auth-status-text', 'children'),
        Output('auth-status-text', 'style'),
        Input('auth-info', 'data')
    )
    def update_auth_status(auth_data):
        """
        Update the authentication status display.

        Args:
            auth_data: Dictionary containing auth information from FastAPI

        Returns:
            Tuple of (status text, style dict)
        """
        if not auth_data or not auth_data.get('authenticated'):
            return 'Not authenticated', {'color': '#999'}

        # User is authenticated
        username = auth_data.get('username', 'User')
        return f'Authenticated as {username}', {'color': '#28a745'}
