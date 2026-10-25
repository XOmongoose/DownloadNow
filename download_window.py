"""IDM-style desktop download details, implemented using standard Tk widgets."""
from pathlib import Path
from engine import safe_name


def format_download_size(info):
    if not info or not isinstance(info.get('bytes'),int) or isinstance(info['bytes'],bool) or info['bytes']<0:
        return 'Dung lượng tệp: Chưa xác định'
    size=info['bytes'];value=float(size);units=('B','KB','MB','GB','TB')
    unit=0
    while value>=1024 and unit<len(units)-1:value/=1024;unit+=1
    amount=(str(size) if unit==0 else f'{value:.1f}'.replace('.',','))+' '+units[unit]
    if info.get('estimated'):return 'Dung lượng tệp: Khoảng '+amount+' (ước tính)'
    exact=f'{size:,}'.replace(',','.')+' byte'
    return 'Dung lượng tệp: '+amount+(f' ({exact})' if unit else '')


def download_details(name, directory, url, remember=True, size_loader=None):
    import tkinter as tk
    from tkinter import filedialog
    result = None
    root = tk.Tk()
    root.title('Download Now — Thông tin tải xuống')
    root.configure(background='#ffffff')
    root.geometry('720x465')
    root.minsize(660,465)
    root.attributes('-topmost',True)
    for icon in (Path(__file__).parent/'DownloadNow.ico',Path(__file__).parent/'build/DownloadNow.ico'):
        if icon.exists():
            try:root.iconbitmap(str(icon))
            except tk.TclError:pass
            break
    root.option_add('*Font',('Segoe UI',10))
    header = tk.Frame(root,bg='#FFF5D6',padx=22,pady=16)
    header.pack(fill='x')
    tk.Label(header,text='↓  Thông tin tải xuống',font=('Segoe UI',18,'bold'),fg='#513E0A',bg='#FFF5D6').pack(anchor='center')
    tk.Label(header,text='Kiểm tra tên tệp và chọn nơi lưu trước khi bắt đầu.',fg='#82795F',bg='#FFF5D6').pack(anchor='center',pady=(4,0))
    form = tk.Frame(root,bg='white',padx=22,pady=14)
    form.pack(fill='both',expand=True)
    form.columnconfigure(0,weight=1)
    url_var, name_var, directory_var = tk.StringVar(value=url),tk.StringVar(value=name),tk.StringVar(value=str(directory))
    remember_var = tk.BooleanVar(value=remember)
    def label(text,row):
        tk.Label(form,text=text,bg='white',fg='#657268').grid(row=row,column=0,columnspan=2,sticky='w',pady=(5,4))
    label('Địa chỉ tải xuống',0)
    tk.Entry(form,textvariable=url_var,state='readonly',readonlybackground='#F7F8F5',relief='solid',bd=1).grid(row=1,column=0,columnspan=2,sticky='ew',ipady=5)
    label('Tên tệp (lấy từ liên kết tải)',2)
    tk.Entry(form,textvariable=name_var,relief='solid',bd=1).grid(row=3,column=0,columnspan=2,sticky='ew',ipady=5)
    size_var=tk.StringVar(value='Dung lượng tệp: Đang kiểm tra…' if size_loader else format_download_size(None))
    tk.Label(form,textvariable=size_var,bg='white',fg='#795800',font=('Segoe UI',10,'bold')).grid(row=4,column=0,columnspan=2,sticky='w',pady=(7,3))
    if size_loader:
        import queue,threading
        sizes=queue.SimpleQueue()
        def load_size():
            try:sizes.put(size_loader())
            except Exception:sizes.put(None)
        def check_size():
            try:size_var.set(format_download_size(sizes.get_nowait()))
            except queue.Empty:root.after(100,check_size)
        threading.Thread(target=load_size,daemon=True).start()
        root.after(100,check_size)
    label('Lưu vào thư mục',5)
    tk.Entry(form,textvariable=directory_var,relief='solid',bd=1).grid(row=6,column=0,sticky='ew',ipady=5)
    def browse():
        current = Path(directory_var.get())
        selected = filedialog.askdirectory(parent=root,title='Chọn thư mục lưu tệp',initialdir=str(current if current.is_dir() else directory))
        if selected:directory_var.set(selected)
    tk.Button(form,text='Duyệt…',command=browse,bg='#FFF5D6',fg='#795800',relief='flat',padx=14,pady=4).grid(row=6,column=1,padx=(10,0))
    tk.Checkbutton(form,text='Ghi nhớ thư mục này cho lần tải sau',variable=remember_var,bg='white',activebackground='white',fg='#513E0A',selectcolor='#FFF5D6').grid(row=7,column=0,columnspan=2,sticky='w',pady=(10,0))
    error = tk.StringVar()
    tk.Label(form,textvariable=error,bg='white',fg='#B2553A',wraplength=660).grid(row=8,column=0,columnspan=2,sticky='w')
    footer = tk.Frame(root,bg='#F8F9F6',padx=22,pady=12)
    footer.pack(fill='x',side='bottom')
    def cancel():root.destroy()
    def accept():
        nonlocal result
        filename = name_var.get().strip()
        folder = Path(directory_var.get()).expanduser()
        if not filename or safe_name(filename)!=filename:
            error.set('Tên tệp không hợp lệ trên Windows. Vui lòng kiểm tra lại.')
            return
        if not folder.is_absolute() or not folder.is_dir():
            error.set('Hãy chọn một thư mục đang tồn tại bằng nút Duyệt…')
            return
        result = {'path':folder.resolve()/filename,'remember':remember_var.get()}
        root.destroy()
    tk.Button(footer,text='Bắt đầu tải',command=accept,bg='#F1AF00',fg='#302600',font=('Segoe UI',10,'bold'),relief='flat',padx=24,pady=8).pack(side='right')
    tk.Button(footer,text='Hủy',command=cancel,bg='white',fg='#657268',relief='flat',padx=20,pady=8).pack(side='right',padx=(0,10))
    root.protocol('WM_DELETE_WINDOW',cancel)
    root.bind('<Escape>',lambda _:cancel())
    root.bind('<Return>',lambda _:accept())
    # Keep the decision window above browser windows until it is dismissed.
    # Schedule activation after Tk has mapped the native window.
    def present():
        root.deiconify()
        root.lift()
        root.focus_force()
    root.after_idle(present)
    root.mainloop()
    return result
