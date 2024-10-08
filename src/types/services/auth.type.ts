import { IPost, IUser } from "../models.type"

export interface IAuthService {
    logOut() : void
    login(loginparams : ILoginParams) : Promise<void>
}

export interface ILoginParams {
    email: string
    password: string
}

export interface IRegisterParams {
    name: string
    email: string
    password: string
    confirm_password: string
}

export interface IAuthResponse {
    access_token: string
    message?:string
    user: IUserResponse
}

export interface IUserResponse {
    user_id: string
    name: string
    email: string
    token_balance: string
    profile: string
    reward_given: string
    reward_received: string
    trophy_given: string
    trophy_received: string
    generate_history: string
    total_price: string
    report_count: string
}