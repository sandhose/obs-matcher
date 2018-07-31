from flask_restplus import fields
from sqlalchemy.exc import IntegrityError

from matcher.exceptions import InvalidTransition


def install_error_handlers(app, api):
    error = api.model('IntegrityError', {
        'type': fields.ClassName(dash=True),
        # Get a kinda raw error message from psycopg
        'message': fields.String(attribute=lambda e: e._message()),
    })

    @app.errorhandler(IntegrityError)
    @api.errorhandler(IntegrityError)
    @api.marshal_with(error, code=400)
    def integrity_error(error):
        """Database integrity error"""
        return error, 400

    error = api.model('InvalidTransition', {
        'type': fields.ClassName(dash=True),
        'message': fields.String(attribute=lambda e: str(e)),
        'from': fields.String(attribute='from_state'),
        'to': fields.String(attribute='to_state'),
    })

    @app.errorhandler(InvalidTransition)
    @api.errorhandler(InvalidTransition)
    @api.marshal_with(error, code=400)
    def invalid_transition(error):
        """Raised when the state transition is invalid is invalid"""
        return error, 400
