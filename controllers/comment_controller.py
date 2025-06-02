from datetime import datetime
from flask import jsonify, request
from flask_login import current_user
from utils.database import db_cursor

def valid_share_token(token):
    """Check if a share token is valid and allows comments"""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT id FROM shared_files 
            WHERE share_token = %s 
            AND (expires_at IS NULL OR expires_at > NOW())
            AND allow_comments = TRUE
        """, (token,))
        return cursor.fetchone() is not None

def save_user_comment(data, user_id):
    """Save comment or reply for authenticated user"""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO comments 
            (file_id, user_id, content, parent_id, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (data['file_id'], user_id, data['content'], data.get('parent_id')))
        comment_id = cursor.lastrowid

        cursor.execute("""
            SELECT users.name, comments.created_at
            FROM users
            JOIN comments ON users.id = comments.user_id
            WHERE comments.id = %s
        """, (comment_id,))

        row = cursor.fetchone()

        return {
            'id': comment_id,
            'user_name': row['name'],
            'content': data['content'],
            'parent_id': data.get('parent_id'),
            'created_at': row['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
            'replies': []
        }

def save_guest_comment(data):
    """Save comment for guest user"""
    guest_name = data.get('guest_name', 'Anonymous')[:50] 
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO comments 
            (file_id, guest_name, content, parent_id, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (data['file_id'], guest_name, data['content'], data.get('parent_id')))
        return cursor.lastrowid
    

def add_comment():
    data = request.get_json()

    if not data.get('file_id') or not data.get('content'):
        return jsonify({'success': False, 'error': 'Missing file_id or content'}), 400

    if not current_user.is_authenticated:
        if not valid_share_token(data.get('share_token')):
            return jsonify({'success': False, 'error': 'Invalid share token'}), 403

        guest_name = data.get('guest_name', 'Anonymous')[:50]
        comment_id = save_guest_comment(data)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({
            'success': True,
            'comment': {
                'id': comment_id,
                'user_name': guest_name,
                'content': data['content'],
                'parent_id': data.get('parent_id'),
                'created_at': created_at,
                'replies': []
            }
        })
    else:
        comment_data = save_user_comment(data, current_user.id)
        return jsonify({
            'success': True,
            'comment': comment_data
        })

def get_comments(file_id):
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, c.guest_name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at ASC
            """, (file_id,))
            comments = cursor.fetchall()

            # Prepare comment objects
            all_comments = [{
                'id': c['id'],
                'content': c['content'],
                'user_name': c['user_name'],
                'created_at': c['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'parent_id': c['parent_id'],
                'replies': []
            } for c in comments]

            # Organize comments by parent-child relationship
            comment_map = {c['id']: c for c in all_comments}
            root_comments = []

            for comment in all_comments:
                if comment['parent_id']:
                    parent = comment_map.get(comment['parent_id'])
                    if parent:
                        parent['replies'].append(comment)
                else:
                    root_comments.append(comment)

            return jsonify({'success': True, 'comments': root_comments})
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

def delete_comment(comment_id):
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM comments 
                WHERE id = %s AND user_id = %s
            """, (comment_id, current_user.id))
            if not cursor.fetchone():
                return jsonify({'error': 'No permission to delete this comment'}), 403
            
            cursor.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
