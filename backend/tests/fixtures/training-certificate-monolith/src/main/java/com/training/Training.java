package com.training;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class Training {

    @Id
    private Long id;
    private String name;
    private String instructor;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getInstructor() {
        return instructor;
    }

    public void setInstructor(String instructor) {
        this.instructor = instructor;
    }
}
