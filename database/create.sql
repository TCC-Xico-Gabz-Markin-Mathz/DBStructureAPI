DROP TABLE IF EXISTS post_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS likes;
DROP TABLE IF EXISTS followers;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP
);

CREATE TABLE posts (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(200),
    content TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE comments (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    user_id INT,
    comment TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE followers (
    follower_id INT NOT NULL,
    followed_id INT NOT NULL,
    PRIMARY KEY (follower_id, followed_id),
    FOREIGN KEY (follower_id) REFERENCES users(id),
    FOREIGN KEY (followed_id) REFERENCES users(id)
);

CREATE TABLE likes (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    user_id INT,
    created_at TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE tags (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50)
);

CREATE TABLE post_tags (
    post_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
-- Inserir 10 usuários
INSERT INTO users (name, email, created_at) VALUES
('João Silva', 'joao@example.com', NOW()),
('Maria Oliveira', 'maria@example.com', NOW()),
('Carlos Santos', 'carlos@example.com', NOW()),
('Ana Paula', 'ana@example.com', NOW()),
('Ricardo Lima', 'ricardo@example.com', NOW()),
('Fernanda Costa', 'fernanda@example.com', NOW()),
('Lucas Rocha', 'lucas@example.com', NOW()),
('Juliana Alves', 'juliana@example.com', NOW()),
('Bruno Martins', 'bruno@example.com', NOW()),
('Camila Pereira', 'camila@example.com', NOW());

-- Inserir 40 posts distribuídos aleatoriamente entre os 10 usuários
INSERT INTO posts (user_id, title, content, created_at) VALUES
(1, 'Primeiro post de João', 'Conteúdo do post de João', NOW()),
(1, 'Segundo post de João', 'Mais conteúdo interessante', NOW()),
(2, 'Post de Maria', 'Maria escreveu algo legal aqui', NOW()),
(3, 'Post de Carlos', 'Carlos falando sobre tecnologia', NOW()),
(3, 'Outro post de Carlos', 'Discussão sobre inovação', NOW()),
(3, 'Mais um de Carlos', 'Carlos é ativo no blog', NOW()),
(4, 'Post da Ana', 'Reflexões da Ana Paula', NOW()),
(5, 'Post do Ricardo', 'Ricardo compartilha ideias', NOW()),
(5, 'Segundo do Ricardo', 'Dicas práticas de Ricardo', NOW()),
(5, 'Terceiro do Ricardo', 'Ricardo está inspirado', NOW()),
(6, 'Post de Fernanda', 'Fernanda fala sobre saúde', NOW()),
(6, 'Mais um de Fernanda', 'Bem-estar e vida saudável', NOW()),
(7, 'Post de Lucas', 'Lucas comenta sobre esportes', NOW()),
(7, 'Outro do Lucas', 'Campeonato em destaque', NOW()),
(7, 'Mais um do Lucas', 'Esportes é com ele mesmo', NOW()),
(7, 'Lucas de novo', 'Futebol é paixão nacional', NOW()),
(8, 'Juliana escreve', 'Moda e estilo com Juliana', NOW()),
(8, 'Juliana de novo', 'Tendências para o verão', NOW()),
(8, 'Outro post', 'Dicas de beleza', NOW()),
(9, 'Bruno fala', 'Notícias e política', NOW()),
(9, 'Bruno comenta', 'Análise de cenário', NOW()),
(10, 'Post de Camila', 'Viagens pelo Brasil', NOW()),
(10, 'Camila escreve', 'Experiência gastronômica', NOW()),
(10, 'Outro de Camila', 'Melhores destinos', NOW()),
(1, 'João volta', 'Novo conteúdo do João', NOW()),
(2, 'Mais um de Maria', 'Receitas de família', NOW()),
(2, 'Outro de Maria', 'Crônicas da vida', NOW()),
(4, 'Ana novamente', 'Diário de bordo', NOW()),
(4, 'Mais Ana', 'Histórias que inspiram', NOW()),
(4, 'E mais Ana', 'Sobre maternidade', NOW()),
(6, 'Fernanda outra vez', 'Treinos e motivação', NOW()),
(6, 'Fernanda escreve', 'Alimentação balanceada', NOW()),
(7, 'Lucas ainda aqui', 'Esportes radicais', NOW()),
(3, 'Carlos comenta', 'Novidades do mercado', NOW()),
(9, 'Bruno analisa', 'Economia e tendências', NOW()),
(10, 'Camila viaja', 'Roteiros internacionais', NOW()),
(5, 'Ricardo encerra', 'Resumo semanal', NOW()),
(8, 'Juliana conclui', 'Moda sustentável', NOW());

-- Inserir alguns seguidores (seguindo entre si aleatoriamente)
INSERT INTO followers (follower_id, followed_id) VALUES
(1, 2),
(2, 3),
(3, 1),
(4, 5),
(5, 4),
(6, 1),
(7, 2),
(8, 3),
(9, 10),
(10, 9);

-- Inserir algumas curtidas em posts
INSERT INTO likes (post_id, user_id, created_at) VALUES
(1, 2, NOW()),
(1, 3, NOW()),
(2, 4, NOW()),
(3, 5, NOW()),
(5, 1, NOW()),
(7, 2, NOW()),
(10, 6, NOW()),
(15, 7, NOW()),
(20, 8, NOW()),
(25, 9, NOW()),
(30, 10, NOW());

-- Inserir alguns comentários
INSERT INTO comments (post_id, user_id, comment, created_at) VALUES
(1, 3, 'Muito bom esse post!', NOW()),
(2, 4, 'Gostei bastante.', NOW()),
(3, 5, 'Parabéns pelo conteúdo!', NOW()),
(4, 1, 'Interessante ponto de vista.', NOW()),
(5, 2, 'Concordo com você.', NOW()),
(6, 3, 'Excelente!', NOW());

-- Inserir algumas tags
INSERT INTO tags (name) VALUES
('tecnologia'),
('esportes'),
('moda'),
('viagem'),
('culinária');

-- Associar algumas tags a posts
INSERT INTO post_tags (post_id, tag_id) VALUES
(1, 1),
(2, 1),
(7, 2),
(8, 2),
(17, 3),
(18, 3),
(22, 4),
(23, 4),
(26, 5),
(27, 5);
