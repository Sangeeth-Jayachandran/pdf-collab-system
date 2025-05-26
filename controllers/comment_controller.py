from flask import jsonify, request
from flask_login import current_user
from utils.database import db_cursor

def add_comment():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    file_id = data.get('file_id')
    content = data.get('content')
    parent_id = data.get('parent_id')
    share_token = data.get('share_token')
    
    if not content or not file_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        with db_cursor() as cursor:
            # Verify access through share token
            if share_token:
                cursor.execute("""
                    SELECT 1 FROM shared_files 
                    WHERE file_id = %s AND share_token = %s
                """, (file_id, share_token))
                if not cursor.fetchone():
                    return jsonify({'error': 'Invalid share token'}), 403
            else:
                # For authenticated users
                if not current_user.is_authenticated:
                    return jsonify({'error': 'Authentication required'}), 401
                cursor.execute("""
                    SELECT 1 FROM pdf_files 
                    WHERE id = %s AND (user_id = %s OR id IN (
                        SELECT file_id FROM shared_files WHERE created_by = %s
                    ))
                """, (file_id, current_user.id, current_user.id))
                if not cursor.fetchone():
                    return jsonify({'error': 'No access to this file'}), 403
            
            # Add comment (user_id will be NULL for guests)
            cursor.execute("""
                INSERT INTO comments (file_id, user_id, content, parent_id)
                VALUES (%s, %s, %s, %s)
            """, (file_id, current_user.get_id() if current_user.is_authenticated else None, content, parent_id))
            
            # Get the new comment
            comment_id = cursor.lastrowid
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.id = %s
            """, (comment_id,))
            new_comment = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'comment': {
                    'id': new_comment['id'],
                    'content': new_comment['content'],
                    'user_name': new_comment['user_name'],
                    'created_at': new_comment['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    'parent_id': new_comment['parent_id']
                }
            })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

def get_comments(file_id):
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at ASC
            """, (file_id,))
            comments = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'comments': [{
                    'id': c['id'],
                    'content': c['content'],
                    'user_name': c['user_name'],
                    'created_at': c['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    'parent_id': c['parent_id']
                } for c in comments]
            })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

def delete_comment(comment_id):
    try:
        with db_cursor() as cursor:
            # Verify ownership
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