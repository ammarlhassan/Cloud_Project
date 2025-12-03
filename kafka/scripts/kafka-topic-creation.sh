#!/bin/bash
################################################################################
# Kafka Topics Creation Script
# Purpose: Create all required Kafka topics for the Cloud-Based Learning Platform
# Author: Cloud-Based Learning Platform Team
# Version: 1.0
################################################################################

set -euo pipefail

# Configuration
KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-kafka-nlb.internal:9092}"
REPLICATION_FACTOR="${REPLICATION_FACTOR:-2}"
MIN_INSYNC_REPLICAS="${MIN_INSYNC_REPLICAS:-2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_topic() {
    local TOPIC_NAME=$1
    local PARTITIONS=$2
    local RETENTION_MS=$3
    local DESCRIPTION=$4

    log_info "Creating topic: $TOPIC_NAME"

    kafka-topics.sh --create \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --topic "$TOPIC_NAME" \
        --partitions "$PARTITIONS" \
        --replication-factor "$REPLICATION_FACTOR" \
        --config min.insync.replicas="$MIN_INSYNC_REPLICAS" \
        --config retention.ms="$RETENTION_MS" \
        --config cleanup.policy=delete \
        --config compression.type=snappy \
        --config segment.ms=86400000 \
        --config segment.bytes=1073741824 \
        --if-not-exists

    if [ $? -eq 0 ]; then
        log_info "✓ Topic '$TOPIC_NAME' created successfully"
    else
        log_error "✗ Failed to create topic '$TOPIC_NAME'"
        return 1
    fi
}

verify_topic() {
    local TOPIC_NAME=$1

    log_info "Verifying topic: $TOPIC_NAME"

    kafka-topics.sh --describe \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --topic "$TOPIC_NAME"
}

################################################################################
# Topic Creation
################################################################################

create_all_topics() {
    log_info "Starting Kafka topics creation..."
    log_info "Bootstrap servers: $KAFKA_BOOTSTRAP_SERVERS"
    log_info "Replication factor: $REPLICATION_FACTOR"
    log_info "Min in-sync replicas: $MIN_INSYNC_REPLICAS"
    echo ""

    # 1. document.uploaded
    create_topic "document.uploaded" 3 604800000 \
        "Triggered when a document is uploaded"

    # 2. document.processed
    create_topic "document.processed" 3 604800000 \
        "Document reading completed"

    # 3. notes.generated
    create_topic "notes.generated" 3 604800000 \
        "Notes created from document"

    # 4. quiz.requested
    create_topic "quiz.requested" 3 259200000 \
        "User requests quiz generation"

    # 5. quiz.generated
    create_topic "quiz.generated" 3 604800000 \
        "Quiz creation completed"

    # 6. audio.transcription.requested
    create_topic "audio.transcription.requested" 6 259200000 \
        "STT request"

    # 7. audio.transcription.completed
    create_topic "audio.transcription.completed" 6 604800000 \
        "STT completed"

    # 8. audio.generation.requested
    create_topic "audio.generation.requested" 6 259200000 \
        "TTS request"

    # 9. audio.generation.completed
    create_topic "audio.generation.completed" 6 604800000 \
        "TTS completed"

    # 10. chat.message
    create_topic "chat.message" 6 2592000000 \
        "Chat interactions"

    echo ""
    log_info "All topics created successfully!"
}

################################################################################
# Topic Verification
################################################################################

verify_all_topics() {
    log_info "Verifying all topics..."
    echo ""

    TOPICS=(
        "document.uploaded"
        "document.processed"
        "notes.generated"
        "quiz.requested"
        "quiz.generated"
        "audio.transcription.requested"
        "audio.transcription.completed"
        "audio.generation.requested"
        "audio.generation.completed"
        "chat.message"
    )

    for topic in "${TOPICS[@]}"; do
        verify_topic "$topic"
        echo ""
    done

    log_info "Topic verification completed!"
}

################################################################################
# List All Topics
################################################################################

list_topics() {
    log_info "Listing all topics..."

    kafka-topics.sh --list \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS"
}

################################################################################
# Delete All Topics (DANGER!)
################################################################################

delete_all_topics() {
    log_warn "WARNING: This will delete ALL topics!"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Aborted."
        return 0
    fi

    TOPICS=(
        "document.uploaded"
        "document.processed"
        "notes.generated"
        "quiz.requested"
        "quiz.generated"
        "audio.transcription.requested"
        "audio.transcription.completed"
        "audio.generation.requested"
        "audio.generation.completed"
        "chat.message"
    )

    for topic in "${TOPICS[@]}"; do
        log_warn "Deleting topic: $topic"
        kafka-topics.sh --delete \
            --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
            --topic "$topic" || true
    done

    log_info "All topics deleted."
}

################################################################################
# Update Topic Configurations
################################################################################

update_topic_config() {
    local TOPIC_NAME=$1
    local CONFIG_KEY=$2
    local CONFIG_VALUE=$3

    log_info "Updating topic '$TOPIC_NAME' config: $CONFIG_KEY=$CONFIG_VALUE"

    kafka-configs.sh --alter \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --entity-type topics \
        --entity-name "$TOPIC_NAME" \
        --add-config "$CONFIG_KEY=$CONFIG_VALUE"

    log_info "✓ Topic configuration updated"
}

################################################################################
# Show Topic Details
################################################################################

show_topic_details() {
    local TOPIC_NAME=$1

    log_info "Topic details for: $TOPIC_NAME"
    echo ""

    # Describe topic
    kafka-topics.sh --describe \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --topic "$TOPIC_NAME"

    echo ""

    # Show configurations
    kafka-configs.sh --describe \
        --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --entity-type topics \
        --entity-name "$TOPIC_NAME"
}

################################################################################
# Main Menu
################################################################################

show_menu() {
    echo ""
    echo "======================================"
    echo "  Kafka Topics Management"
    echo "======================================"
    echo "1. Create all topics"
    echo "2. Verify all topics"
    echo "3. List all topics"
    echo "4. Show topic details"
    echo "5. Update topic configuration"
    echo "6. Delete all topics (DANGER!)"
    echo "7. Exit"
    echo "======================================"
    echo ""
}

main() {
    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -p "Select an option: " choice

            case $choice in
                1)
                    create_all_topics
                    ;;
                2)
                    verify_all_topics
                    ;;
                3)
                    list_topics
                    ;;
                4)
                    read -p "Enter topic name: " topic_name
                    show_topic_details "$topic_name"
                    ;;
                5)
                    read -p "Enter topic name: " topic_name
                    read -p "Enter config key: " config_key
                    read -p "Enter config value: " config_value
                    update_topic_config "$topic_name" "$config_key" "$config_value"
                    ;;
                6)
                    delete_all_topics
                    ;;
                7)
                    log_info "Exiting..."
                    exit 0
                    ;;
                *)
                    log_error "Invalid option"
                    ;;
            esac
        done
    else
        # Command-line mode
        case $1 in
            create)
                create_all_topics
                ;;
            verify)
                verify_all_topics
                ;;
            list)
                list_topics
                ;;
            delete)
                delete_all_topics
                ;;
            *)
                log_error "Unknown command: $1"
                echo "Usage: $0 {create|verify|list|delete}"
                exit 1
                ;;
        esac
    fi
}

# Run main function
main "$@"
