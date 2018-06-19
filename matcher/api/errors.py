from flask_restplus import fields
from sqlalchemy.exc import IntegrityError
from matcher.exceptions import InvalidStatusTransition


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

    error = api.model('InvalidStatusTransition', {
        'type': fields.ClassName(dash=True),
        'message': fields.String(attribute=lambda e: str(e)),
        'from': fields.String(attribute='from_status'),
        'to': fields.String(attribute='to_status'),
    })

    @app.errorhandler(InvalidStatusTransition)
    @api.errorhandler(InvalidStatusTransition)
    @api.marshal_with(error, code=400)
    def invalid_status_transition(error):
        """Raised when the scrap status is invalid"""
        return error, 400
