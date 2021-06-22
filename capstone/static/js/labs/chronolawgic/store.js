import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

// eslint-disable-next-line
const importUrls = urls; // defined in timeline.html
// eslint-disable-next-line
const importChoices = choices; // defined in timeline.html
// eslint-disable-next-line
const importUser = user; // defined in timeline.html

importChoices.colors = [
    "#00db67",
    "#ccff6d",
    "#dbc600",
    "#db8f00",
    "#ff8e7a",
    "#ff736c",
    "#e5435c",
    "#986d81",
    "#7e84ff",
    "#3656f6",
    "#2f2f2f",
    "#3e667a",
    "#00b7db",
    "#c4c4c4",
];

// jurisdictions
const jurisdictions = [];
for (let i = 0; i < importChoices.jurisdictions.length; i++) {
    jurisdictions.push(importChoices.jurisdictions[i][1])
}
importChoices.jurisdictions = jurisdictions;

// courts
const courts = [];
for (let i = 0; i < importChoices.courts.length; i++) {
    courts.push({
        slug: importChoices.courts[i][0],
        courtName: importChoices.courts[i][1]
    })
}
importChoices.courts = courts;

function getBestError(error) {
    // eslint-disable-next-line
    // debugger;
    if (error && Object.prototype.hasOwnProperty.call(error, "response") &&
        Object.prototype.hasOwnProperty.call(error.response, "data") &&
        Object.prototype.hasOwnProperty.call(error.response.data, "reason")) {
        if (Object.prototype.hasOwnProperty.call(error.response.data, "details")) {
            return error.response.data.reason + ": " + error.response.data.details
        }
        return error.response.data.reason
    }
    return error
}

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        mobileEventsExpanded: false,
        breakPoint: 'lg',
        user: importUser,
        choices: importChoices,
        requestStatus: 'nominal', // can be nominal, success, error, or pending. Prone to race conditions, so use only for user feedback until its improved
        notificationMessage: null,
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: importUrls.chronolawgic_api_create,
            chronolawgic_api_retrieve: importUrls.chronolawgic_api_retrieve,
            chronolawgic_api_update: importUrls.chronolawgic_api_update,
            chronolawgic_api_delete: importUrls.chronolawgic_api_delete,
            chronolawgic_api_update_admin: importUrls.chronolawgic_api_update_admin,
            chronolawgic_api_create_h2o: importUrls.chronolawgic_api_create_h2o,

            api_delete_category: importUrls.api_delete_category,
            api_add_category: importUrls.api_add_category,
            api_update_category: importUrls.api_update_category,
            api_delete_case: importUrls.api_delete_case,
            api_add_case: importUrls.api_add_case,
            api_update_case: importUrls.api_update_case,
            api_delete_event: importUrls.api_delete_event,
            api_add_event: importUrls.api_add_event,
            api_update_event: importUrls.api_update_event,

            static: importUrls.static,
            api_root: importUrls.api_root,
        },
        availableTimelines: [],
        minimized: true,
        id: 1,
        title: "",
        description: "",
        createdBy: -1, // (user accts are for auth/logging purposes)
        isAuthor: false,
        author: '', // user-added string
        categories: [],
        events: [],
        cases: [],
        stats: [],
        firstYear: 1900,
        lastYear: 2000,
        templateEvent: {
            name: "",
            short_description: "",
            long_description: "",
            start_date: "",
            end_date: "",
            url: "",
            color: "",
        },
        templateCase: {
            url: "",
            name: "",
            citation: "",
            short_description: "",
            long_description: "",
            jurisdiction: "",
            reporter: "",
            decision_date: "",
            categories: [],
            color: "",
        },
        templateCategory: {
            name: "",
            shape: "",
            color: ""
        },
        missingCases: {}
    },
    mutations: {
        expandMobileEvents(state) {
            state.mobileEventsExpanded = true
        },
        setBreakPoint(state, newBreakPoint) {
            state.breakPoint = newBreakPoint
        },
        unExpandMobileEvents(state) {
            state.mobileEventsExpanded = false
        },
        toggleMinimized(state) {
            state.minimized = !state.minimized
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {
            state.title = json.title;
            state.author = json.author ? json.author : "CAP User";
            state.description = json.description;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases;
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id;
        },
        setCreatedBy(state, createdBy) {
            state.createdBy = createdBy;
        },
        setAuthor(state, isAuthor) {
            state.isAuthor = isAuthor;
        },
        setCategories(state, categories) {
            state.categories = categories;
        },
        setStats(state, stats) {
            state.stats = stats;
        },
        setFirstYear(state, year) {
            state.firstYear = year;
        },
        setLastYear(state, year) {
            state.lastYear = year;
        },
        setRequestStatus(state, status) {
            state.requestStatus = status;
        },
        setRequestStatusTerminal(state, status) {
            state.requestStatus = status;
            setTimeout(function () {
                state.requestStatus = "nominal";
            }, 5000);
        },
        setNotificationMessage(state, message) {
            //TODO Someday— make this a queue and let the notifications stack
            state.notificationMessage = message;
            setTimeout(function () {
                state.notificationMessage = null;
            }, 5000);
        },
        addEvent(state, event) {
            // assign id to event
            event.id = this.generateUUID();
            state.events.push(event);
            this.dispatch('requestUpdateTimeline')
        },
        addCase(state, caselaw) {
            // assign id to caselaw
            caselaw.id = this.generateUUID();
            state.cases.push(caselaw);
            this.dispatch('requestUpdateTimeline')
        },
        updateEvent(state, event) {
            for (let i = 0; i < state.events.length; i++) {
                if (state.events[i].id === event.id) {
                    state.events[i] = event;
                    this.dispatch('requestUpdateTimeline');
                    break;
                }
            }
        },
        updateCase(state, caselaw) {
            for (let i = 0; i < state.cases.length; i++) {
                if (state.cases[i].id === caselaw.id) {
                    state.cases[i] = caselaw;
                    this.dispatch('requestUpdateTimeline');
                    break;
                }
            }
        },
        deleteEvent(state, id) {
            let event_index = -1;
            for (let i = 0; i < state.events.length; i++) {
                if (state.events[i].id === id) {
                    event_index = i;
                    break;
                }
            }
            state.events.splice(event_index, 1);
            this.dispatch('requestUpdateTimeline');
        },
        deleteCase(state, id) {
            let caselaw_index = -1;
            for (let i = 0; i < state.cases.length; i++) {
                if (state.cases[i].id === id) {
                    caselaw_index = i;
                    break;
                }
            }
            state.cases.splice(caselaw_index, 1);
            this.dispatch('requestUpdateTimeline');
        },
        saveCategories(state, categories) {
            state.categories = categories;
            for (let i = 0; i < state.categories.length; i++) {
                if (!(state.categories[i].id)) {
                    state.categories[i].id = store.generateUUID()
                }
            }
            this.dispatch('requestUpdateTimeline');
        },
        setMissingCases(state, missingCases) {
            state.missingCases = missingCases;
        }
    },
    getters: {
        breakPoint: state => state.breakPoint,
        isMobile: (state) => {
            return state.breakPoint === 'xs' || state.breakPoint === 'sm';
        },
        mobileEventsExpanded: state => state.mobileEventsExpanded,
        minimized: state => state.minimized,
        cases: state => state.cases,
        choices: state => state.choices,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        notificationMessage: state => state.notificationMessage,
        templateEvent: state => state.templateEvent,
        templateCase: state => state.templateCase,
        templateCategory: state => state.templateCategory,
        empty: (state) => {
            if (state.requestStatus === 'pending') {
                return 'pending'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events') &&
                !Object.prototype.hasOwnProperty.call(state, 'events') ) {
                return 'empty'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events')) {
                return state.cases.length === 0 ? 'empty' : 'populated'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'cases') ) {
                return state.events.length === 0 ? 'empty' : 'populated'
            }
            return state.events.length + state.cases.length === 0 ? 'empty' : 'populated';
        },
        firstYear: (state) => {
            if (state.cases.length === 0 && state.events.length === 0) {
                return 0
            }
            let first_case_year = 9999999;
            let first_event_year = 9999999;
            if (state.events.length) {
                first_event_year = state.events.reduce((min, e) =>
                    new Date(e.start_date).getUTCFullYear() < min ? new Date(e.start_date).getUTCFullYear() : min, new Date(state.events[0].start_date).getUTCFullYear());
            }
            if (state.cases.length) {
                first_case_year = state.cases.reduce((min, c) => new Date(c.decision_date).getUTCFullYear() < min ? new Date(c.decision_date).getUTCFullYear() : min, new Date(state.cases[0].decision_date).getUTCFullYear());
            }
            return first_case_year < first_event_year ? first_case_year : first_event_year;
        },
        lastYear: (state) => {
            if (state.cases.length === 0 && state.events.length === 0) {
                return 0
            }
            let last_event_year = 0;
            let last_case_year = 0;
            if (state.events.length) {
                last_event_year = state.events.reduce((max, e) =>
                    new Date(e.end_date).getUTCFullYear() > max ? new Date(e.end_date).getUTCFullYear() : max, new Date(state.events[0].end_date).getUTCFullYear());
            }
            if (state.cases.length) {
                last_case_year = state.cases.reduce((max, e) =>
                    new Date(e.decision_date).getUTCFullYear() > max ? new Date(e.decision_date).getUTCFullYear() : max, new Date(state.cases[0].decision_date).getUTCFullYear());
            }
            return last_case_year > last_event_year ? last_case_year : last_event_year;
        },
        events: (state) => {
            return state.events.sort((a, b) => (a.start_date > b.start_date) ? 1 : -1)
        },
        eventByStartYear: (state) => (year) => {
            return state.events.filter(evt => {
                return new Date(evt.start_date).getUTCFullYear() === year;
            })
        },
        casesByYear: (state) => (year) => {
            return state.cases.filter(cas => {
                return year === new Date(cas.decision_date).getUTCFullYear();
            })
        },
        timeline: (state) => {
            return {
                title: state.title,
                author: state.author,
                events: state.events,
                cases: state.cases,
                categories: state.categories,
                description: state.description
            }
        },
        categories: (state) => {
            return state.categories
        },
        category: (state) => (id) => {
            return state.categories.find(cat => cat.id === id)
        },
        randomColor: (state) => {
            return state.colors[Math.floor(Math.random() * state.colors.length)]
        },
        stats: (state) => {
            return state.stats;
        },
        missingCases: (state) => {
            return state.missingCases;
        }
    },
    actions: {
        requestCreateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .post(this.state.urls.chronolawgic_api_create)
                .then(response => response.data)
                .then(new_tl => {
                    if (new_tl.status === "ok") {
                        this.dispatch('requestTimelineList');
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', 'Timeline Created')
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
            })
        },
        requestDeleteTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .delete(this.state.urls.chronolawgic_api_delete + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        this.dispatch('requestTimelineList');
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', "Timeline Deleted")
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error deleting timeline: " + getBestError(error))
            })
        },
        requestUpdateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            let json = JSON.stringify({timeline: this.getters.timeline});
            axios
                .post(this.state.urls.chronolawgic_api_update + this.state.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Timeline Saved")
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestDeleteCase: function ({commit}, caseId) {
            commit('setRequestStatus', 'pending');
            let case_delete_url = this.state.urls.api_delete_case.replace('__TIMELINE_ID__', this.state.id).replace('__CASE_ID__', caseId)
            console.log(case_delete_url);
            return axios
                .delete(case_delete_url, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        this.dispatch('requestRefreshTimeline', "Deleted Case").then(() => {
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', "Deleted Timeline")
                        })
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestAddUpdateCase: function ({commit}, case_object) {
            commit('setRequestStatus', 'pending');
            let case_update_url = this.state.urls.api_add_update_case.replace('__TIMELINE_ID__', this.state.id);
            let case_update_payload = JSON.stringify(case_object);
            return axios
                .post(case_update_url, case_update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Case Added")
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestDeleteEvent: function ({commit}, eventId) {
            commit('setRequestStatus', 'pending');
            let event_delete_url = this.state.urls.api_delete_event.replace('__TIMELINE_ID__', this.state.id).replace('__CASE_ID__', eventId)
            console.log(event_delete_url);
            return axios
                .delete(event_delete_url, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        this.dispatch('requestRefreshTimeline', "Deleted Event").then(() => {
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', "Deleted Timeline")
                        })
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestAddUpdateEvent: function ({commit}, event_object) {
            commit('setRequestStatus', 'pending');
            let event_update_url = this.state.urls.api_add_update_event.replace('__TIMELINE_ID__', this.state.id);
            let event_update_payload = JSON.stringify(event_object);
            return axios
                .post(event_update_url, event_update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Event Added")
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestDeleteCategory: function ({commit}, categoryId) {
            commit('setRequestStatus', 'pending');
            let category_delete_url = this.state.urls.api_delete_category.replace('__TIMELINE_ID__', this.state.id).replace('__CASE_ID__', categoryId)
            console.log(category_delete_url);
            return axios
                .delete(category_delete_url, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        this.dispatch('requestRefreshTimeline', "Deleted Category").then(() => {
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', "Deleted Timeline")
                        })
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestAddUpdateCategory: function ({commit}, category_object) {
            commit('setRequestStatus', 'pending');
            let category_update_url = this.state.urls.api_add_update_category.replace('__TIMELINE_ID__', this.state.id);
            let category_update_payload = JSON.stringify(category_object);
            return axios
                .post(category_update_url, category_update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Category Added")
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestTimeline: function ({commit}, timelineId) {
            // clear timeline if it exists
            commit('setTimelineId', '');
            commit('setTimeline', {title: ''});

            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimelineId', timeline['id']);
                        commit('setTimeline', timeline['timeline']);
                        commit('setCreatedBy', timeline['created_by']);
                        commit('setAuthor', timeline['is_owner'])
                        commit('setStats', timeline['stats'])
                        commit('setFirstYear', timeline['first_year'])
                        commit('setLastYear', timeline['last_year'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error retrieving timeline: " + getBestError(error))
            })
        },
        requestRefreshTimeline: function ({commit, getters}) {
            // clear timeline if it exists
            return axios
                .get(this.state.urls.chronolawgic_api_retrieve + getters.id)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimeline', timeline['timeline']);
                    }
                }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error retrieving timeline: " + getBestError(error))
                })
        },
        requestTimelineList: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve)
                .then(response => response.data)
                .then(availableTimelines => {
                    if (availableTimelines.status === "ok") {
                        commit('setAvailableTimelines', availableTimelines['timelines'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error retrieving timeline list: " + getBestError(error))
            })
        },
        requestUpdateAdmin: function ({commit}, data) {
            commit('setRequestStatus', 'pending');
            let author = data.author.trim();
            let json = JSON.stringify({
                title: data.title,
                // don't allow empty strings
                author: author ? author : "CAP User",
                description: data.description,
            });

            return axios
                .post(this.state.urls.chronolawgic_api_update_admin + data.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Change Saved")
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
                })
        },
        requestCreateH2OTimeline: function ({commit}, data) {
            let json = JSON.stringify(data)
            return axios.post(this.state.urls.chronolawgic_api_create_h2o, json, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => response.data)
                .then(
                    (new_tl) => {
                        if (new_tl.status === "ok") {
                            this.dispatch('requestTimelineList');
                        }
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Timeline Created")
                        return new_tl
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
                    return error
                })

        }
    }
});

store.generateUUID = () => {
    // https://stackoverflow.com/a/2117523/2247227
    return 'xxxxxxxxxx'.replace(/[xy]/g, function (c) {
        let r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}


export default store;