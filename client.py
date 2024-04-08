import json
import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox
CHATCONTENT = 'chatcontent'
CHAT_EXIT = '|exit|'
CHAT_USERS = 'chatusers'
CHAT_REG_NICKNAME = 'reg_nickname'
CHAT_PRIVATE = 'private'


class Gui_Client:

    def __init__(self):
        self.clist = {}  # Store the accessed socket client as a dictionary with the client's username.
        self.namelist = list()
        self.t = None
        self.ChatGUI()

    def ChatGUI(self):
        #GUI
        self.root = tk.Tk()  # 整个窗口
        self.root.geometry('800x350')
        self.root.title("Welcome to the Multi-User Chat System")
        self.info_frame = tk.Frame(self.root)
        self.info_frame.pack(fill=tk.X, side=tk.TOP)
        self.server_frame = tk.LabelFrame(
            self.root, text="Chat room settings", padx=5, pady=5)
        self.server_frame.pack(fill=tk.X, side=tk.TOP)

        # user list box
        self.name_var = tk.StringVar()
        self.lb = tk.Listbox(self.info_frame, listvariable=self.name_var, width=20, selectmode=tk.EXTENDED)
        self.lb.bind('<ButtonRelease-1>', self.one_to_one)  #  Binds the left mouse button click event.
        self.lb.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        self.ybar = tk.Scrollbar(self.info_frame)
        self.ybar.pack(fill=tk.Y, side=tk.RIGHT)
        self.out = tk.Text(self.info_frame, width=50, height=15)
        insert_text(self.out, 'Welcome to the Multi-User Chat System!')
        self.out.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        self.top_server = tk.Frame(self.server_frame, )
        self.top_server.pack(fill=tk.X, padx=(10, 0))

        self.nickname_frame = tk.Frame(self.top_server)
        self.nickname_frame.pack(side=tk.LEFT, padx=5)

        self.nickname_entry = tk.Entry(self.nickname_frame, width=20)
        self.nickname_entry.pack(side=tk.LEFT, padx=5)

        self.set_nickname_button = tk.Button(self.nickname_frame, text="Set Nickname", command=self.set_nickname)
        self.set_nickname_button.pack(side=tk.LEFT, padx=5)

        tk.Label(self.top_server, width=5).pack(side=tk.LEFT)

        #IP address
        self.connection_frame = tk.Frame(self.top_server)
        self.connection_frame.pack(side=tk.RIGHT, padx=5)

        self.ip_var = tk.StringVar()
        self.ip_var.set('127.0.0.1')
        self.ip_entry = tk.Entry(self.connection_frame, textvariable=self.ip_var, width=15)
        self.ip_entry.pack(side=tk.LEFT, padx=5)

        self.port_var = tk.IntVar()
        self.port_var.set(5555)
        self.port_entry = tk.Entry(self.connection_frame, textvariable=self.port_var, width=5)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.start_btn = tk.Button(self.connection_frame, text="Connecting to the server", command=self.client_Start, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.down_server = tk.Frame(self.server_frame, )
        self.down_server.pack(fill=tk.X, side=tk.BOTTOM)

        self.that_var = tk.StringVar()
        self.that = tk.Entry(
            self.down_server, textvariable=self.that_var, width=40)
        self.that.pack(fill=tk.X, side=tk.LEFT)

        self.end_btn = tk.Button(
            self.down_server, text="send", width=15, command=self.sendMsg).pack(side=tk.LEFT)
        self.root.protocol('WM_DELETE_WINDOW', self.close_window)
        self.root.mainloop()


    def set_nickname(self):
        self.nickname = self.nickname_entry.get().strip()
        if self.nickname:  # Check if the nickname is empty
            self.nickname_entry.config(state=tk.DISABLED)
            self.set_nickname_button.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
        else:
            messagebox.showerror("warning", "Please enter a nickname.")
            self.start_btn.config(state=tk.DISABLED)

    def close_window(self):
       # Window closes, closing all connections
        if self.t:
            data = {'protocol': CHAT_EXIT, 'data': '|exit|'}
            data1 = json.dumps(data)
            try:
                self.t.s.send(data1.encode('utf-8'))
                self.root.destroy()
            except:
                self.root.destroy()
                sys.exit()
        else:
            self.root.destroy()
            print("The window has been closed.")



    def client_Start(self):
        if not self.nickname:
            messagebox.showerror("Connection Error", "Please set a nickname before connecting to the server.")
            return

        try:
            self.t = TcpClient(self.ip_var.get(), self.port_var.get(), self.name_var, self.namelist, self.out,
                               self.clist, self.nickname)
            self.t.start()
            self.start_btn.config(state=tk.DISABLED)
            insert_text(self.out, "{} joined the chat!\nConnected to the server!".format(self.nickname))

        except Exception as e:
            messagebox.showinfo("warning", "The server is not running")
            print(e, 'The server is not running')

    def sendMsg(self):
        # Private Chat Content The header should include @+nickname, which is used to determine whether to send a private chat.
        msg = self.that.get()

        if msg.find("@") == 0:
            data = retOneToOneJsonData(msg)
            outmsg = 'Send a private message to '+data['name']+':'+data['data']
            if self.t:
                if self.t.send_json(data):
                    insert_text(self.out,outmsg)
                    self.that_var.set('')
        else:
            # public chat
            data = {'protocol': CHATCONTENT, 'data': msg}
            if self.t:
                if self.t.send_json(data):
                    insert_text(self.out, msg)
                else:
                    print("warning", "please connect to server.")
            else:
                messagebox.showinfo("warning", "please connect to server.")
                print("warning", "please connect to server.")
            self.that_var.set('')

    def one_to_one(self, event):

        items = self.lb.curselection()
        if items:
            selected_username = self.lb.get(items[0])
            self.that_var.set(f"@{selected_username} ")
            self.that.focus()


class TcpClient(threading.Thread):
    def __init__(self, addr, port, name_var, namelist, out, clist, name):
        threading.Thread.__init__(self)
        self.addr = addr
        self.port = port
        self.name_var = name_var
        self.namelist = namelist
        self.out = out
        self.clist = clist
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.addr, self.port))
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.stop_flag = False
        self.name = name
        self.msgdata = ''
        self.isOk = 1

    def run(self):
        self.inThat()

    def inThat(self):
        while not self.stop_flag:
            if self.isOk:
                self.isNameOk()
            try:
                msg = self.rece_json(self.s.recv(1024).decode())
                if msg['protocol'] == CHAT_EXIT:  # Exit
                    insert_text(self.out, msg)
                    break
                if msg['protocol'] == CHAT_USERS:
                    self.namelist.clear()
                    self.namelist = msg['data']
                    self.name_var.set(self.namelist)
                if msg['protocol'] == CHATCONTENT:
                    insert_text(self.out, msg['data'])
                    print('Receive messages from the server:', msg['data'])
            except Exception as e:
                print('Receive message thread is closed', e)
                break
        msg = 'you have logged out of the chat room.'
        insert_text(self.out, msg)
        self.stop()

    def isNameOk(self):
        while True:
            if self.isOk:
                usernamedata = {'protocol': CHAT_REG_NICKNAME, 'data': self.name}
                self.send_json(usernamedata)  # Send nickname to server for verification
                self.isOk = 0
            tempjson = self.rece_json(self.s.recv(1024))
            if tempjson['protocol'] == CHAT_USERS:
                print('Receive user list')
                self.namelist.clear()
                self.namelist = tempjson['data']
                self.name_var.set(self.namelist)
                break

    def send_json(self, msg):
        # Send a message in json format to the server
        data = json.dumps(msg)
        try:
            self.s.send(data.encode('utf-8'))
            return 1
        except:
            messagebox.showinfo("warning", "Please connect to the server.")
            return 0

    def rece_json(self, data):
        jsondata = json.loads(data)
        print(jsondata)
        return jsondata

    def stop(self):
        self.s.close()
        self.stop_flag = True


def retOneToOneJsonData(msg):
    # Returns the data sent by the private chat

    # Get user name
    name = msg.split(" ")[0].lstrip("@")
    skey = msg.split(" ")[0]
    data = msg.replace(skey+" ", "")
    return {'protocol': CHAT_PRIVATE, 'data': data, 'name': name}


def insert_text(out, msg):
    out.insert(tk.END, msg + '\n')
    out.see(tk.END)


def main():
    Gui_Client()


if __name__ == '__main__':
    main()