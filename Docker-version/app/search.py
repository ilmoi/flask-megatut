# all the functionality related to elasticsearch is here, so that it's easy to swap it out later if we have to
# specifically we need 3 functions - add something to index, remove, query
# the other good thing about this funcitonality is that it's GENERIC - we can apply it to any model we want

from flask import current_app


def add_to_index(index, model):
    # remember we added elasticsearch as an attribute to the flask app we're creating in __init__
    # if the env variable is disabled
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    # elasticsearch needs a unique ID for each doc and so we're using the ID from the model (which is also conveniently unique)
    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [],0
    # multi-match searches across numerous fields
    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']