package com.inha.capstone.user.domain;

import com.inha.capstone.common.domain.BaseEntity;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "users")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "hashed_password", nullable = false, length = 255)
    private String password;

    @Column(name = "token_version", nullable = false)
    private Integer tokenVersion;

    @Column(name = "is_active", nullable = false)
    private Boolean isActive;

    @Builder
    public User(String email, String username, String name, String password) {
        this.email = email;
        this.username = username;
        this.name = name;
        this.password = password;
        this.tokenVersion = 0;
        this.isActive = true;
    }

    public void increaseTokenVersion() {
        this.tokenVersion++;
    }
}
