from flask import jsonify
from matcher.exceptions import InvalidStatusTransition


def install_error_handlers(app, api):
    @api.errorhandler(InvalidStatusTransition)
    @app.errorhandler(InvalidStatusTransition)
    def invalid_status_transition(error):
        """When the status is invalid"""
        return jsonify({
            'message': str(error),
            'from': str(error.from_status),
            'to': str(error.to_status),
        }), 400
