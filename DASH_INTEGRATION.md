# QDB Dash Integration Guide

This guide explains how to integrate the QDB Dash application with your existing FastAPI server.

## Overview

The QDB Dash application is a Plotly Dash web interface for the Quantity Database. It provides:
- Search interface for flowables, contexts, and quantities
- Detail views for individual entities
- Analysis tools for selected items

## File Structure

```
xdb/api/
├── qdb_dash.py                    # Main Dash app
└── qdb_dash_components/
    ├── __init__.py
    ├── banner.py                  # Top banner component
    ├── banner_callbacks.py        # Banner callbacks
    ├── landing.py                 # Search/landing page
    ├── landing_callbacks.py       # Search callbacks with STUBS
    ├── detail.py                  # Detail page with STUBS
    ├── analyze.py                 # Analysis page
    └── analyze_callbacks.py       # Analysis callbacks with STUBS
```

## Installation

First, ensure you have the required dependencies:

```bash
pip install dash dash-bootstrap-components a2wsgi plotly pandas
```

## Integration Steps

### 1. Mount the Dash App in FastAPI

In your `xdb/api/qdb.py` file, add the following at the top (after imports):

```python
from a2wsgi import WSGIMiddleware
from xdb.api.qdb_dash import create_dash_app
```

Then, after your router definition, add:

```python
# Create and mount the Dash app
dash_app = create_dash_app()

# You can mount this in your main FastAPI app or in the qdb_router
# Option 1: Mount in the router (recommended)
# This will be available at /qdb/dash/*
# Add this line in your main app setup where you include the router:
# app.mount("/qdb/dash", WSGIMiddleware(dash_app.server))

# Option 2: Add a route that includes the Dash app
# See the main app file for mounting instructions
```

### 2. Mount in Your Main FastAPI Application

In your main FastAPI application file (likely where you create the FastAPI app instance), add:

```python
from a2wsgi import WSGIMiddleware
from xdb.api.qdb_dash import dash_app

# After including your routers:
app.include_router(qdb_router)

# Mount the Dash app
app.mount("/qdb/dash", WSGIMiddleware(dash_app.server))
```

### 3. Serve Static Assets

The Dash app expects logo images at:
- `/qdb/dash/assets/qdb.png`
- `/qdb/dash/assets/wordmark-Antelope-fixed.png`

These files should already exist in `xdb/api/assets/`. The Dash framework will automatically serve files from an `assets` folder if you create one:

```bash
# Create assets directory for Dash
mkdir -p xdb/api/assets
# Your logo files should already be there based on the concept document
```

Alternatively, you can configure FastAPI to serve these static files:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/qdb/dash/assets", StaticFiles(directory="xdb/api/assets"), name="qdb_assets")
```

### 4. Implement Backend Stubs

The following functions in the components need to be connected to your backend:

#### `landing_callbacks.py` - `search_backend(query, entity_type)`

Replace the stub with actual backend search:

```python
def search_backend(query, entity_type):
    """
    Search the backend for entities matching the query.

    Args:
        query: Search string
        entity_type: Type of entity to search ('flowable', 'context', 'quantity')

    Returns:
        List of dicts with 'id' and 'name' keys
    """
    # Example implementation using your runtime resources:
    from xdb.api.runtime import cat, lcia

    if entity_type == 'flowable':
        # Search for flowables in your catalog
        results = []
        for flow in cat.flows(search=query):
            results.append({'id': flow.external_ref, 'name': flow.name})
        return results[:20]  # Limit to 20 results

    elif entity_type == 'context':
        # Search for contexts
        results = []
        for cx in lcia.contexts():
            if query.lower() in str(cx).lower():
                results.append({'id': str(cx), 'name': str(cx)})
        return results[:20]

    elif entity_type == 'quantity':
        # Search for quantities
        results = []
        for q in lcia.quantities(search=query):
            results.append({'id': q.external_ref, 'name': q.name})
        return results[:20]

    return []
```

#### `detail.py` - `get_entity_details(entity_type, entity_id)`

Replace the stub with actual entity retrieval:

```python
def get_entity_details(entity_type, entity_id):
    """
    Retrieve detailed information about an entity from the backend.

    Args:
        entity_type: Type of entity ('flowable', 'context', 'quantity')
        entity_id: ID of the entity

    Returns:
        Dictionary with entity details, or None if not found
    """
    from xdb.api.runtime import cat, lcia

    try:
        if entity_type == 'flowable':
            entity = cat.get(entity_id)
            return {
                'name': entity.name,
                'id': entity.external_ref,
                'reference_quantity': str(entity.reference_entity),
                'cas_number': entity.get('cas_number', 'N/A'),
                # Add other properties as needed
            }

        elif entity_type == 'context':
            cx = lcia[entity_id]
            return {
                'name': str(cx),
                'id': entity_id,
                'elementary': cx.elementary,
                'sense': cx.sense,
                'parent': str(cx.parent) if cx.parent else None,
            }

        elif entity_type == 'quantity':
            q = lcia.get_canonical(entity_id)
            return {
                'name': q.name,
                'id': q.external_ref,
                'unit': q.unit,
                'is_lcia_method': q.is_lcia_method,
                # Add other properties as needed
            }

    except Exception:
        return None
```

#### `analyze.py` - `analyze_selection(selection_data)`

Replace the stub with actual analysis logic:

```python
def analyze_selection(selection_data):
    """
    Analyze the user's selection and return results.

    Args:
        selection_data: Dictionary with flowables, contexts, quantities lists

    Returns:
        Dictionary with analysis results (dataframes, charts, etc.)
    """
    import pandas as pd
    from xdb.api.runtime import cat, lcia

    # Example: Create a summary table of selected items
    rows = []

    for flowable_id in selection_data.get('flowables', []):
        try:
            flow = cat.get(flowable_id)
            rows.append({
                'Type': 'Flowable',
                'Name': flow.name,
                'ID': flowable_id,
                'Details': str(flow.reference_entity)
            })
        except Exception:
            pass

    for context_id in selection_data.get('contexts', []):
        try:
            cx = lcia[context_id]
            rows.append({
                'Type': 'Context',
                'Name': str(cx),
                'ID': context_id,
                'Details': f"Elementary: {cx.elementary}"
            })
        except Exception:
            pass

    for quantity_id in selection_data.get('quantities', []):
        try:
            q = lcia.get_canonical(quantity_id)
            rows.append({
                'Type': 'Quantity',
                'Name': q.name,
                'ID': quantity_id,
                'Details': f"Unit: {q.unit}"
            })
        except Exception:
            pass

    df = pd.DataFrame(rows)

    return {
        'dataframe': df,
        'chart_data': None  # Add chart data if needed
    }
```

### 5. Authentication Integration

To pass authentication information from FastAPI to Dash, you can modify the Dash app to read authentication from the Flask request context:

In `qdb_dash.py`, add a callback that reads auth info from request headers:

```python
from flask import request

@dash_app.server.before_request
def check_authentication():
    """
    Extract authentication information from FastAPI and store in Dash.
    FastAPI should pass this via headers or session.
    """
    # Example: Read from custom header
    auth_token = request.headers.get('Authorization')

    # You can then validate this token and set user info
    # This is just a placeholder - implement according to your auth system
    pass
```

## Testing the Integration

1. Start your FastAPI server
2. Navigate to `http://localhost:8000/qdb/dash/` (adjust port as needed)
3. You should see the QDB search interface with the banner

## Customization

### Styling

The app uses Dash Bootstrap Components with the default BOOTSTRAP theme. To change the theme, modify the `external_stylesheets` in `qdb_dash.py`:

```python
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],  # or DARKLY, SOLAR, etc.
    requests_pathname_prefix=requests_pathname_prefix,
    suppress_callback_exceptions=True
)
```

### Adding Custom Pages

To add a new page:

1. Create a new component file in `qdb_dash_components/`
2. Create corresponding callbacks file
3. Update the routing callback in `qdb_dash.py`
4. Import and register the callbacks in `register_callbacks()`

## Troubleshooting

### Assets Not Loading

If logos don't appear:
- Check that files exist in `xdb/api/assets/`
- Verify the static files mount point
- Check browser console for 404 errors

### Callbacks Not Firing

- Ensure all callback IDs match between components and callbacks
- Check for duplicate callback outputs
- Look for JavaScript errors in browser console

### WSGI Integration Issues

- Ensure `a2wsgi` is installed: `pip install a2wsgi`
- Check that the mount path doesn't conflict with existing routes
- Verify `requests_pathname_prefix` matches the mount path

## Next Steps

1. Implement the stub functions with your actual backend logic
2. Test all three pages (landing, detail, analyze)
3. Add error handling and user feedback
4. Implement export functionality in the analyze page
5. Add authentication checks to sensitive operations
