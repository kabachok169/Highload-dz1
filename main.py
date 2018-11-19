#!/usr/bin/env python

import os
import socket
import threading
from datetime import datetime
from urllib import unquote
from contextlib import closing


def make_common_response_headers():
    date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    headers = 'Server: WIMWSOP\n'
    headers += 'Connection: close\n'
    headers += 'Date: {}\n'.format(date)
    return headers


def parse_config(config_path):
    if not os.path.exists(config_path):
        print 'Config file at {} does not exists'.format(config_path)

    config = {
        'listen': 80,
        'thread_limit': 8,
        'document_root': '/var/www/html'
    }

    with open(config_path) as config_file:
        for line in config_file.readlines():
            key, value = line.split()[0:2]
            if key in config.keys():
                config[key] = value
            else:
                print 'Wrong config line: {} {}'.format(key, value)

    return config


def make_error_response(code):
    error_codes = {405: 'Method Not Allowed',
                   404: 'Not Found',
                   403: 'Forbidden'}
    if code not in error_codes.keys():
        raise ValueError('Unallowed error code: {}'.format(code))
    response = 'HTTP/1.1 {} {}\n'.format(code, error_codes[code])
    response += make_common_response_headers()
    response += "Content-Type: text/html; charset=UTF-8\n"
    response += '\n'
    return response


def get_full_path(path, document_root):
    path = path[:-1] + '/index.html' if path[-1] == '/' else path
    return document_root + path


def get_content_type(path):
    content_types = {
        '.txt': 'text/txt',
        '.html': 'text/html',
        '.css': 'text/css',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.js': 'application/javascript',
        '.swf': 'application/x-shockwave-flash',
        }
    file_name, file_extension = os.path.splitext(path)
    return 'Content-Type: {}'.format(content_types.get(file_extension, 'text/txt'))


def make_head_response(path):
    try:
        with open(path) as file:
            body = file.read()
    except IOError:
        return make_error_response(404)
    response = 'HTTP/1.1 200 OK\r\n'
    response += make_common_response_headers()
    response += '\r\nContent-Length: {}\r\n\r\n'.format(len(body))
    return response


def make_get_response(path):
    try:
        with open(path) as file:
            body = file.read()
    except IOError:
        return make_error_response(404)

    response = 'HTTP/1.1 200 OK\r\n'
    response += make_common_response_headers()
    response += get_content_type(path)
    response += '\r\nContent-Length: {}\r\n'.format(len(body))
    response += '\r\n'
    response += body
    return response


def make_response(request, document_root):
    # print request
    headers_part = request.split('\r\n\r\n')[0]
    headers_lines = headers_part.split('\r\n')
    method, path, version = headers_lines[0].split()
    path = unquote(path).split('?')[0]
    full_path = get_full_path(path, document_root)

    if '/..' in path:
        return make_error_response(404)

    if ('index.html' in full_path) and not os.path.exists(full_path):
        return make_error_response(403)

    if method == 'HEAD':
        return make_head_response(full_path)
    elif method == 'GET':
        return make_get_response(full_path)
    else:
        return make_error_response(405)


def handle_requests(sock, document_root):
    while True:
        connection, address = sock.accept()

        data = connection.recv(2048)
        if len(data.strip()) == 0:
            connection.close()
            continue

        connection.sendall(make_response(data, document_root))
        connection.close()
        

def start_server(config):
    thread_pool = []
    port_number = int(config['listen'])

    thread_limit = int(config['thread_limit'])
    document_root = config['document_root']

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port_number))
        sock.listen(thread_limit)

        for i in range(thread_limit):
            thread_pool.append(threading.Thread(target=handle_requests, args=(sock, document_root)))
            thread_pool[i].start()

        for i in range(thread_limit):
            thread_pool[i].join()


if __name__ == '__main__':
    config = parse_config('./httpd.conf')

    start_server(config)
