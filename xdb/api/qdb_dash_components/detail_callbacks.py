"""
Detail Page Callbacks

Callbacks for updating detail page button states based on selection.
"""

from dash import Input, Output, State, ALL, no_update
import logging


def register(app):
    """Register detail page callbacks."""

    @app.callback(
        Output({'type': 'detail-add-button', 'index': ALL}, 'children'),
        Output({'type': 'detail-add-button', 'index': ALL}, 'color'),
        Input('user-selection', 'data'),
        State({'type': 'detail-add-button', 'index': ALL}, 'id'),
    )
    def update_detail_buttons(selection_data, button_ids):
        """
        Update all detail page add/remove buttons based on selection state.

        Args:
            selection_data: Current user selection
            button_ids: List of button IDs on the page

        Returns:
            Tuple of (children_list, color_list) for all buttons
        """
        logging.warning(f'update detail {button_ids}')
        if not button_ids:
            return no_update, no_update

        children_list = []
        color_list = []

        for btn_id in button_ids:
            entity_type, entity_id = btn_id['index'].split(':', 1)

            lookfor = {'flowable': 'flowables',
                       'context': 'contexts',
                       'quantity': 'quantities'}[entity_type]  # :eyeroll:

            # Check if selected
            is_selected = entity_id in selection_data.get(f'{lookfor}', [])

            if is_selected:
                children_list.append('Remove from Selection')
                color_list.append('primary')
            else:
                children_list.append('Add to Selection')
                color_list.append('success')

        logging.warning(f'update detail finish {children_list} {color_list}')

        return children_list, color_list

    @app.callback(
        Output('user-selection', 'data', allow_duplicate=True),
        Input({'type': 'detail-add-button', 'index': ALL}, 'n_clicks'),
        State('user-selection', 'data'),
        State({'type': 'detail-add-button', 'index': ALL}, 'id'),
        prevent_initial_call=True
    )
    def detail_add_to_selection(n_clicks_list, selection_data, button_ids):
        """
        Handle add/remove from selection on detail page.

        Args:
            n_clicks_list: List of click counts
            selection_data: Current user selection
            button_ids: List of button IDs

        Returns:
            Updated selection data
        """
        from dash import ctx
        logging.warning(f'detail add {n_clicks_list}')

        if not ctx.triggered_id:
            return no_update

        # Check if this was an actual click
        triggered_value = ctx.triggered[0]['value']
        if triggered_value is None or triggered_value == 0:
            return no_update

        # Get the clicked button's index
        button_index = ctx.triggered_id['index']
        entity_type, entity_id = button_index.split(':', 1)

        logging.warning(f'detail add_to_selection {button_index}')

        # Create new selection
        new_selection = {
            'flowables': selection_data.get('flowables', []).copy(),
            'contexts': selection_data.get('contexts', []).copy(),
            'quantities': selection_data.get('quantities', []).copy()
        }

        # Toggle selection
        if entity_type == 'flowable':
            if entity_id in new_selection['flowables']:
                new_selection['flowables'].remove(entity_id)
            else:
                new_selection['flowables'].append(entity_id)
        elif entity_type == 'context':
            if entity_id in new_selection['contexts']:
                new_selection['contexts'].remove(entity_id)
            else:
                new_selection['contexts'].append(entity_id)
        elif entity_type == 'quantity':
            if entity_id in new_selection['quantities']:
                new_selection['quantities'].remove(entity_id)
            else:
                new_selection['quantities'].append(entity_id)

        return new_selection
