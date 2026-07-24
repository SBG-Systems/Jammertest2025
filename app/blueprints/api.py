from flask import Blueprint, current_app, jsonify

from app.storage.cache_manager import get_or_create_cache

api_bp = Blueprint('api', __name__)

@api_bp.route('/data')
def get_all_data():
    memory_store = get_or_create_cache()
    data = memory_store.get_all_latest()
    return jsonify(data)

@api_bp.route('/data/<ins_id>')
def get_data(ins_id):
    memory_store = get_or_create_cache()
    return jsonify(memory_store.get_latest(ins_id))

@api_bp.route('/positions')
def get_positions():
    memory_store = get_or_create_cache()
    return jsonify(memory_store.get_positions(last_minutes=5))

@api_bp.route('/reboot/<ins_id>', methods=['POST'])
def reboot(ins_id):
    monitor = current_app.config['MONITOR']
    try:
        monitor.reboot(ins_id)
        return jsonify({'success': True})
    except KeyError:
        return jsonify({'success': False, 'error': f'Unknown device {ins_id}'}), 404
    except NotImplementedError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502

@api_bp.route('/reboot', methods=['POST'])
def reboot_all():
    monitor = current_app.config['MONITOR']
    results = monitor.reboot_all()
    return jsonify(results)
