import mysql from 'mysql2/promise';
import 'dotenv/config';

function parseUrl(url) {
  if (!url) return null;
  const clean = url.replace('mysql+mysqlconnector://', 'mysql://');
  const u = new URL(clean);
  return {
    host: u.hostname,
    user: u.username,
    password: u.password,
    database: u.pathname.slice(1),
    port: u.port || 3306,
  };
}

const base = parseUrl(process.env.DATABASE_URL) || {
  host: 'localhost',
  user: 'root',
  password: '',
  database: 'macmarket',
  port: 3306,
};

const pool = mysql.createPool({
  ...base,
  waitForConnections: true,
  connectionLimit: 10,
});

export function query(sql, params) {
  return pool.execute(sql, params);
}
