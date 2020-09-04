from flask import Flask, render_template, request, session, make_response, redirect, url_for, flash
import sqlite3
import os.path
import bcrypt
from marshmallow import Schema,fields,validate


app = Flask(__name__)
app.secret_key = 'my_secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db.db")

class CreateFormularioRegistroSchema(Schema):
    email = fields.Str(required=True, validate=validate.Email(), data_key='email')
    password = fields.Str(required=True, validate=validate.Length(min=5, max=15), data_key='password')
    id = fields.Str(required=True, data_key='id')
    name = fields.Str(required=True, data_key='name')
    lastname = fields.Str(required=True, data_key='lastname')
    address = fields.Str(required=True, data_key='address')
    phone = fields.Str(required=True, data_key='phone')
    
class CreateLoginSchema(Schema):
    email = fields.Str(required=True, validate=validate.Email(), data_key='email')
    password = fields.Str(required=True, validate=validate.Length(min=5, max=15), data_key='pass')


create_formulario_registro_schema = CreateFormularioRegistroSchema()
create_login_schema = CreateLoginSchema()


@app.route('/')
def homepage():
    #Si hay un mensaje de error retornara al login, con una alerta de tipo error
    if 'mensaje' in request.args:
        mensaje =  request.args["mensaje"]
        return render_template('login.html',alerta = mensaje)
    if 'user' in session:
        email = session['user']  
        con_bd = sqlite3.connect('db.db')
        #cursor a la db 
        cursor_db = con_bd.cursor()
        sql = "SELECT nombres, lastname FROM  users WHERE correo=?"
        cursor_db.execute(sql, (email,))
        nombres_usuarios = cursor_db.fetchone()
        sql = "SELECT * FROM  products"
        cursor_db.execute(sql)
        productos = cursor_db.fetchall()
        nombres_usuarios=nombres_usuarios[0]+" "+nombres_usuarios[1]
        return render_template('products.html',usuario_registrado=nombres_usuarios.upper(), products = productos)
    return render_template('login.html')


@app.route('/compras/<codigo_producto>', methods=['POST'])
def insertar_compra(codigo_producto):
    if 'user' in session:
        cantidad = request.form["cantidad"]
        session['carrito'] = session['carrito'] + codigo_producto +","+ cantidad+ ";"
        return redirect(url_for('homepage'))
    else:
        mensaje = "su sesión ha caducado, por favor vuelva a autenticarse"
        return render_template('mensaje.html', mensaje=mensaje)


@app.route('/login', methods=['POST'])
def login_users():
    errors = create_login_schema.validate(request.form)
    if errors:
        mensaje='danger'
        flash('Usuario o contraseña incorrectos')
        return redirect(url_for('homepage',mensaje = mensaje))
    #datos enviados por el usuario
    email = request.form["email"]
    password = request.form["pass"]
    #se consulta a la base de datos si existe el usuario
    #si existe, entonces se recupera su password
    con_bd = sqlite3.connect('db.db')
    #cursor a la db
    cursor_db = con_bd.cursor()
    #consultas
    sql = "SELECT contraseña FROM  users WHERE correo=?"
    cursor_db.execute(sql, (email,))
    fila = cursor_db.fetchone()
    if fila is not None:
        aux_pass = bytes(password, encoding= 'utf-8')
        if bcrypt.checkpw(aux_pass, fila[0]):
            session['user'] =  email
            session['carrito'] = ""
            sql = "SELECT nombres, lastname FROM  users WHERE correo=?"
            cursor_db.execute(sql, (email,))
            fila = cursor_db.fetchone()
            usuario_registrado=fila[0]+" "+fila[1]
            sql = "SELECT * FROM  products"
            cursor_db.execute(sql)
            productos = cursor_db.fetchall()
            return render_template('products.html',usuario_registrado=usuario_registrado.upper() ,products = productos )
        else:
            mensaje='danger'
            flash('Usuario o contraseña incorrectos')
            return redirect(url_for('homepage',mensaje = mensaje))
    else:
        mensaje='danger'
        flash('Usuario o contraseña incorrectos')
        return redirect(url_for('homepage', mensaje = mensaje))


@app.route('/register' , methods=['POST'])
def register_user():
    errors = create_formulario_registro_schema.validate(request.form)
    if errors:
        mensaje='danger'
        flash('ingreso de datos incorrectos, INTENTELO NUEVAMENTE')
        return redirect(url_for('homepage',mensaje = mensaje))
    document= request.form["id"]
    nombres= request.form["name"]
    apellidos= request.form["lastname"]
    direccion= request.form["address"]
    telefono= request.form["phone"]
    correo= request.form["email"]
    contraseña= request.form["password"]
    aux_pass=bytes(contraseña, encoding='utf-8')
    salt= bcrypt.gensalt()
    hashPassword= bcrypt.hashpw(aux_pass, salt)
    #conexion a la base de datos
    con_bd = sqlite3.connect('db.db')
    #cursor a la db
    cursor_agenda = con_bd.cursor()
    sql = "SELECT * FROM users WHERE documento = ?"
    cursor_agenda.execute(sql,(document,))
    fila = cursor_agenda.fetchone()
    if fila is not None:
        flash('El numero de identificacion ya esta registrado')
        return redirect(url_for('homepage', mensaje='danger'))
    else:    
        #consultas
        cursor_agenda.execute("INSERT INTO users(documento, nombres, lastname, direccion, telefono, correo, contraseña) VALUES(?, ?, ?, ?, ?, ?, ?)",(document,nombres,apellidos,direccion,telefono,correo,hashPassword))
        #se ejecutan los cambios
        con_bd.commit()
        #cierre del cursor
        cursor_agenda.close()
        #cierre de la conexion
        con_bd.close()
        flash('Registro Exitoso!!')
        return redirect(url_for('homepage',mensaje='primary'))


@app.route('/logout')
def logout_users():
    if 'user' in session:
        session.pop('user')
    return render_template('login.html')


@app.route('/verCompras')
def ver_compras():
    carrito=session['carrito']
    if carrito == "":
        flash('No tiene productos añadidos al carrito')
        return redirect(url_for('homepage'))
    if 'user' in session:
        carrito = session['carrito']
        correo = session['user']
        compra_total = []
        with sqlite3.connect(db_path) as con_bd:
            cursor_db = con_bd.cursor()
            sql = "SELECT nombres, lastname FROM  users WHERE correo=?"
            cursor_db.execute(sql, (correo,))
            nombres_usuarios = cursor_db.fetchone()
            nombres_usuarios=nombres_usuarios[0]+" "+nombres_usuarios[1]
            #aqui se separan los productos en lista (producto,cantidad; producto,cantidad)
            elementos = carrito.split(";") #los separa por ;
            total=0
            iva=0
            pago=0
            for i in range (len(elementos)-1): #hace este proceso la cantidad de veces segun la cantidad de productos q el usuario comprara
                producto_cantidad=elementos[i].split(",")#separa los elementos de la lista por , osea queda codigo y cantidad
                cursor_db = con_bd.cursor()
                sql = "SELECT * FROM products WHERE codigo =? "
                cursor_db.execute(sql,(producto_cantidad[0],))#selecciona  el codigo q se recogio la ruta compras 
                referencia_producto = cursor_db.fetchall()#guarda el producto seleccionado como una tupla
                referencia_producto_cantidad = referencia_producto[0]#codigo del producto 
                referencia_producto_cantidad =list(referencia_producto_cantidad)#ya no es tupla, si no lista,de codigo.
                referencia_producto_cantidad.pop(3)
                referencia_producto_cantidad.insert(3,producto_cantidad[1])
                vtotal = float(producto_cantidad[1]) * float(referencia_producto_cantidad[2])#[2] recoge el valor del prodcuto en la bd
                vtotal1=vtotal*0.19
                vtotal2=vtotal-vtotal1
                total+=vtotal2
                iva+=vtotal1
                pago=total+iva
                referencia_producto_cantidad.insert(4,vtotal2)
                referencia_producto_cantidad = tuple(referencia_producto_cantidad)
                compra_total.append(referencia_producto_cantidad)
                print(referencia_producto_cantidad)
            return render_template('compras.html', compras = compra_total, total=total,iva=iva, pago=pago,usuario_registrado = nombres_usuarios.upper())    
    else:
        flash('Sesion Caducada')
        return render_template('login.html', alerta="warning")

@app.route('/pagar')
def pagar():


    if 'user' in session:
        carrito = session['carrito']
        correo = session['user']
        with sqlite3.connect(db_path) as con_bd:
            cursor_db = con_bd.cursor()
            sql = "SELECT nombres, lastname FROM  users WHERE correo=?"
            cursor_db.execute(sql, (correo,))
            nombres_usuarios = cursor_db.fetchone()
            nombres_usuarios=nombres_usuarios[0]+" "+nombres_usuarios[1]
            elementos = carrito.split(";") 
            total=0
            iva=0
            pago=0
            for i in range (len(elementos)-1): 
                producto_cantidad=elementos[i].split(",")
                cursor_db = con_bd.cursor()
                sql = "SELECT * FROM products WHERE codigo =? "
                cursor_db.execute(sql,(producto_cantidad[0],))
                referencia_producto = cursor_db.fetchall()
                referencia_producto_cantidad = referencia_producto[0]
                referencia_producto_cantidad =list(referencia_producto_cantidad)
                referencia_producto_cantidad.pop(3)
                referencia_producto_cantidad.insert(3,producto_cantidad[1])
                vtotal = float(producto_cantidad[1]) * float(referencia_producto_cantidad[2])
                vtotal1=vtotal*0.19
                vtotal2=vtotal-vtotal1
                total+=vtotal2
                iva+=vtotal1
                pago=total+iva
                referencia_producto_cantidad.insert(4,vtotal)
                referencia_producto_cantidad = tuple(referencia_producto_cantidad)
                sql = "INSERT INTO compras(codigo_producto,nombre_producto, precio,cantidad,valor_total,cliente) VALUES(?,?,?,?,?,?)"
                cursor_db.execute(sql, (referencia_producto_cantidad[0],referencia_producto_cantidad[1],referencia_producto_cantidad[2],referencia_producto_cantidad[3],referencia_producto_cantidad[4],correo))
                con_bd.commit()
            return render_template('compraExitosa.html', pago=pago, usuario_registrado = nombres_usuarios.upper())
 
    else:
        flash('Sesion Caducada')
        return render_template('login.html', alerta="warning")







if __name__ == '__main__':
    app.run(port = 3000, debug = True)