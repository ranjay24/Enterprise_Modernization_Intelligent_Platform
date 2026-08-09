package com.training;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

import java.time.LocalDate;

@Entity
public class Certificate {

    @Id
    private Long id;
    private String holderName;
    private LocalDate issuedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getHolderName() {
        return holderName;
    }

    public void setHolderName(String holderName) {
        this.holderName = holderName;
    }

    public LocalDate getIssuedAt() {
        return issuedAt;
    }

    public void setIssuedAt(LocalDate issuedAt) {
        this.issuedAt = issuedAt;
    }
}
