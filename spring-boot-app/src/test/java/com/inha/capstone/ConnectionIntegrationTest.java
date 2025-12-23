package com.inha.capstone;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.bson.Document;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@DisplayName("데이터베이스 연결 테스트")
class ConnectionIntegrationTest {

    @Autowired
    private DataSource dataSource;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private MongoTemplate mongoTemplate;

    @Autowired
    private ElasticsearchOperations elasticsearchOperations;

    @Autowired
    private ElasticsearchClient elasticsearchClient;

    @Test
    void PostgreSQL_연결_테스트() throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            assertThat(connection.isValid(1)).isTrue();
        }
        
        Integer result = jdbcTemplate.queryForObject("SELECT 1", Integer.class);
        assertThat(result).isEqualTo(1);
    }

    @Test
    void Redis_연결_테스트() {
        String key = "test:connection";
        String value = "active";
        
        redisTemplate.opsForValue().set(key, value);
        Object retrievedStatus = redisTemplate.opsForValue().get(key);
        
        assertThat(retrievedStatus).isEqualTo(value);
        
        redisTemplate.delete(key);
    }

    @Test
    void MongoDB_연결_테스트() {
        Document pong = mongoTemplate.executeCommand("{ ping: 1 }");
        assertThat(pong).containsKey("ok");
    }



    @Test
    void Elasticsearch_연결_테스트() throws java.io.IOException {
        assertThat(elasticsearchClient.ping().value()).isTrue();
    }
}
