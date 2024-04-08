import json
import socket
import sys
import threading
import time
import tkinter as tk


CHATCONTENT = 'chatcontent'
CHAT_EXIT = '|exit|' #exit chat
CHAT_USERS = 'chatusers'
CHAT_REG_NICKNAME = 'reg_nickname'
CHAT_PRIVATE = 'private'


class GuiServer:

    def __init__(self):
        self.is_server_start = 0
        self.t = None
        self.root = tk.Tk()
        self.root.geometry('800x300')
        self.root.title("Welcome to the Multi-User Chat System")
        self.info_frame = tk.Frame(self.root)  # Stores user lists
        self.info_frame.pack(fill=tk.X, side=tk.TOP)
        self.server_frame = tk.LabelFrame(self.root, text="Chat room settings", padx=5, pady=5)
        self.server_frame.pack(fill=tk.X, side=tk.TOP)

        # user list box
        self.name_var = tk.StringVar()
        self.lb = tk.Listbox(self.info_frame, listvariable=self.name_var, width=20, selectmode=tk.EXTENDED)
        self.lb.pack(fill=tk.Y, side=tk.LEFT)

        self.ybar = tk.Scrollbar(self.info_frame)
        self.ybar.pack(fill=tk.Y, side=tk.RIGHT)

        self.out = tk.Text(self.info_frame, width=50, height=15)
        insert_text(self.out, 'Welcome to the Multi-User Chat System')
        self.out.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        self.top_server = tk.Frame(self.server_frame, )
        self.top_server.pack(fill=tk.X, side=tk.TOP)
        #Ip
        self.ip_var = tk.StringVar()
        self.ip_var.set('127.0.0.1')
        self.ip_entry = tk.Entry(
            self.top_server, textvariable=self.ip_var, width=12)
        self.ip_entry.pack(fill=tk.X, side=tk.LEFT)
        # port
        self.port_var = tk.IntVar()
        self.port_var.set(5555)
        self.port_entry = tk.Entry(self.top_server, textvariable=self.port_var, width=5)
        self.port_entry.pack(side=tk.LEFT)

        self.start_btn = tk.Button(self.top_server, text="Start Server", width=18, command=self.server_start).pack(side=tk.LEFT)

        self.down_server = tk.Frame(self.server_frame, )
        self.down_server.pack(fill=tk.X, side=tk.BOTTOM)

        self.root.protocol('WM_DELETE_WINDOW', self.close_window)
        self.root.mainloop()

    def close_window(self):
      # Window closes, closing all connections
        if self.t.cs:
            for k, v in self.t.cs.items():
                users_data = {'protocol': CHAT_USERS, 'data': []}
                jsondata = json.dumps(users_data, ensure_ascii=False)
                self.t.cs[k].send(jsondata.encode('utf-8'))
                self.t.cs[k].close()
                self.t.cts[k].stop_flag = True

            self.t.stop_flag = True
            self.root.destroy()
            print('The server is closed...')
            sys.exit()

        else:
            self.root.destroy()
            print('The program exits and the window closes.')

    def server_start(self):
        self.t = TcpServer(self.ip_var.get(), self.port_var.get(), self.name_var, self.out, )  # 创建一个聊天室服务器线程
        self.t.start()
        insert_text(self.out, 'Server is running...')
        print('Server is running...')
        self.is_server_start = 1


class TcpServer(threading.Thread):
    def __init__(self, addr, port, name_var, out):
        threading.Thread.__init__(self)
        self.cts = dict()  # Dictionary holding client threads
        self.cs = dict()  # Store the accessed socket client as a dictionary with the client's username.
        self.namelist = list()
        self.addr = addr
        self.port = port
        self.name_var = name_var
        self.out = out
        #connection-oriented
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Creates a socket object.
        self.s.bind((self.addr, self.port))
        self.s.listen(5)  # Set maximum number of connections, queue when exceeded.
        self.stop_flag = False

    def run(self):
        while not self.stop_flag:
            self.recieve_msg()


    def recieve_msg(self):
        if not self.stop_flag:
            csock, car = self.s.accept()
            csock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print("Discover client Connections")
            vnt = ClientNameT(csock, car, self.cts, self.cs, self.name_var, self.namelist, self.out)
            vnt.start()


    def stop(self):
        self.stop_flag = True

# Multi-threaded handling of new user connections
class ClientNameT(threading.Thread):
    def __init__(self, csock, car, cts, cs, name_var, namelist, out):
        threading.Thread.__init__(self)
        self.csock = csock
        self.car = car
        self.cs = cs
        self.cts = cts
        self.name_var = name_var
        self.namelist = namelist  # 在线列表
        self.out = out  # 服务器信息打印框

    def additem(self, name):
        self.namelist.append(name)
        self.name_var.set(self.namelist)

    def run(self):
        while True:
            username_json = self.csock.recv(1024).decode()
            name_data = json.loads(username_json)
            print('Create a new client thread and add it to the client dictionary.')
            if name_data['protocol'] == CHAT_REG_NICKNAME:
                name = name_data['data']
                original_name = name
                suffix = 1
                # Check if the username already exists, and if so, add a numeric suffix
                while name in self.namelist:
                    name = f"{original_name}{suffix}"
                    suffix += 1
                self.additem(name)
                self.cs[name] = self.csock
                sendlisttousers(self.cs, self.namelist)  # Send the list of used users to everyone
                print('Send the list of used users to everyone')
                st = SocketThread(self.csock, self.car, self.cts, self.cs, self.name_var, self.namelist, self.out, name)  #
                st.Daemon = True
                self.cts[name] = st
                st.start()
                time.sleep(1)
                msg = '%s has joined the chat room.\n' % name
                data = {'protocol': CHATCONTENT, 'data': msg}
                for k in self.cs:  # The loop dictionary prints the message for each socket so that each client gets the message.
                    print(name, k)
                    if name != k:
                        send_json(self.cs[k], data)
                insert_text(self.out, msg)
                break


#Multi-threaded client handling, if a socket connection is created a thread is created to handle it.
class SocketThread(threading.Thread):
    def __init__(self, csock, car, cts, cs, name_var, namelist, out, name):
        threading.Thread.__init__(self)
        self.csock = csock
        self.car = car
        self.cs = cs
        self.cts = cts
        self.name_var = name_var
        self.namelist = namelist
        self.out = out
        self.name = name
        self.stop_flag = False

    def run(self):
        while True:
            try:
                #Accepting data from a connected client
                json_data = self.csock.recv(1024).decode()
                print("Received message from {}".format(self.name))
                data = rece_json(json_data)
            except Exception:
                print('client already closed')

            if data['protocol'] == CHAT_EXIT:
                break
            # If the chat is public, it is sent to everyone
            if data['protocol'] == CHATCONTENT:
                insert_text(self.out, self.name + ':' + data['data'])
                jsondata = {'protocol': CHATCONTENT, 'data': self.name + ':' + data['data']}
                for k in self.cs:
                    send_json(self.cs[k], jsondata)

            if data['protocol'] == CHAT_PRIVATE:
                insert_text(self.out, self.name + ' send a private message to ' + data['name'] + ':' + data['data'])
                jsondata = {'protocol': CHATCONTENT, 'data': self.name + ' send a private message to you:' + data['data']}
                send_json(self.cs[data['name']], jsondata)

        if not self.stop_flag:
            msg1 = '{} has left the chat room, Disconnected from the server'.format(self.name)
            msg2 = '{} disconnected from the server'.format(self.name)
            jsondata1 = {'protocol': CHATCONTENT, 'data': msg1}
            jsondata2 = {'protocol': CHATCONTENT, 'data': msg2}
            insert_text(self.out, msg1)
            print(msg2)

            for k in self.cs:
                send_json(self.cs[k], jsondata1)

                if self.name == k:
                    send_json(self.cs[k], jsondata2)
            self.cs.pop(self.name)

            self.namelist.clear()
            for n in self.cs.items():
                self.namelist.append(n[0])
            self.name_var.set(self.namelist)  # Reload the user list
            sendlisttousers(self.cs, self.namelist)  # Send the list of used users to everyone
            print('Sending user list to everyone.')
            self.csock.close()

def insert_text(out, msg1):
    out.insert(tk.END, msg1 + '\n')
    out.see(tk.END)

def rece_json(data):

    jsondata = json.loads(data)
    return jsondata


def send_json(s, msg):
    data = json.dumps(msg) + '\n'
    try:
        s.send(data.encode('utf-8'))
        return True
    except Exception as e:
        print("Error sending message: ", e)
        return False


def sendlisttousers(cs, namelist):
    # Send the list of used users to everyone
    users_data = {'protocol': CHAT_USERS, 'data': namelist}
    jsondata = json.dumps(users_data, ensure_ascii=False)
    for k in cs:
        cs[k].send(jsondata.encode('utf-8'))

if __name__ == '__main__':
    GuiServer()