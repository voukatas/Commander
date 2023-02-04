CREATE TABLE IF NOT EXISTS hosts (
    uuid text PRIMARY KEY,
    type text,
    ip text NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    uuid text NOT NULL,
    task text NOT NULL,
    FOREIGN KEY (uuid) REFERENCES hosts (uuid)
);


CREATE TABLE IF NOT EXISTS results (
    uuid text NOT NULL,
    result text NOT NULL,
    FOREIGN KEY (uuid) REFERENCES hosts (uuid)
);